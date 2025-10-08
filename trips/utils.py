import hashlib
import time

import folium
import requests
from django.core.cache import cache
from django.db.models import BooleanField, Case, F, Max, Min, Q, When, Window
from django.db.models.functions import Lag, Lead

from accounts.models import Profile
from trips.models import Trip


def annotate_event_overlaps(queryset):
    """
    Annotates events with overlap information using window functions.
    An event overlaps when either:
    - Its start time is before the next event's end time
    - Its end time is after the previous event's start time

    Returns: Queryset annotated with has_overlap boolean field
    """
    return queryset.annotate(
        next_start=Window(
            expression=Lead("start_time"), partition_by="day_id", order_by="start_time"
        ),
        prev_end=Window(
            expression=Lag("end_time"), partition_by="day_id", order_by="start_time"
        ),
    ).annotate(
        has_overlap=Case(
            When(
                Q(end_time__gt=F("next_start")) | Q(start_time__lt=F("prev_end")),
                then=True,
            ),
            default=False,
            output_field=BooleanField(),
        )
    )


def get_trips(user):
    """Get the trips for the home page with favourite trip (if present) and others"""
    fav_trip = Profile.objects.get(user=user).fav_trip or None
    if fav_trip:
        other_trips = (
            Trip.objects.filter(author=user).exclude(pk=fav_trip.pk).order_by("status")
        )
    else:
        other_trips = Trip.objects.filter(author=user).order_by("status")
    context = {
        "other_trips": other_trips,
        "fav_trip": fav_trip,
    }
    return context


def rate_limit_check():
    """Rate limiting for Nominatim - max 1 request per second"""
    last_request_time = cache.get("nominatim_last_request_time", 0)
    current_time = time.time()

    # Wait if the last request was less than 1 second ago
    time_diff = current_time - last_request_time
    if time_diff < 1:
        time.sleep(1 - time_diff)

    # Update the last request time in cache
    cache.set("nominatim_last_request_time", time.time(), 60)


def generate_cache_key(name, city):
    """Unique cache key for geocoding requests"""
    # Normalize name and city to lower case and strip whitespace
    normalized = f"{name.lower().strip()}_{city.lower().strip()}"
    # Use a hash function to create a unique key
    return (
        f"geocode_{hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()}"
    )


def geocode_location(name, city):
    """Geocoding using Nominatim OpenStreetMap with cache and rate limiting. Returns a list of addresses ordered by importance."""
    if not name or not city:
        return None

    # Check cache first
    cache_key = generate_cache_key(name, city)
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    # Rate limit check to avoid hitting Nominatim too fast
    rate_limit_check()

    time.sleep(
        1
    )  # Ensure at least 1 second between requests for showing a meaningfiul indicator on the frontend
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{name.strip()}, {city.strip()}",
        "format": "json",
        "limit": 5,  # Get up to 5 results to choose the best one
        "addressdetails": 1,
    }

    headers = {"User-Agent": "OrganizeIt-Geocoding"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            results = response.json()
            if not results:
                return []

            # Build a list of addresses with importance
            address_list = []
            for result in results:
                address_data = result.get("address", {})
                addresstags = result.get("addresstags", {})
                street = (
                    addresstags.get("street")
                    or address_data.get("road")
                    or address_data.get("pedestrian")
                    or address_data.get("footway")
                    or ""
                )
                housenumber = (
                    addresstags.get("housenumber")
                    or address_data.get("house_number")
                    or ""
                )
                city_part = (
                    addresstags.get("city")
                    or address_data.get("city")
                    or address_data.get("town")
                    or address_data.get("village")
                    or ""
                )
                address_parts = []
                if street:
                    address_parts.append(street)
                if housenumber:
                    address_parts.append(housenumber)
                address = " ".join(address_parts)
                if address and city_part:
                    address = f"{address}, {city_part}"
                elif city_part:
                    address = city_part
                address_list.append(
                    {
                        "name": result.get("name", ""),
                        "address": address,
                        "lat": float(result.get("lat", 0)),
                        "lon": float(result.get("lon", 0)),
                        "importance": result.get("importance", 0),
                        "place_rank": result.get("place_rank", 999),
                    }
                )

            # Order the list by importance descending
            address_list.sort(key=lambda x: x["importance"], reverse=True)
            cache.set(cache_key, address_list, 3600)
            return address_list

    except Exception as e:
        print(f"Error geocoding: {e}")

    return []


def select_best_result(results, name, city):
    """Select the best result from Nominatim results based on custom scoring"""
    if not results:
        return None

    city_lower = city.lower().strip()
    name_lower = name.lower().strip()

    # Scoring results based on various criteria
    scored_results = []

    for result in results:
        score = 0
        display_name = result.get("display_name", "").lower()
        address = result.get("address", {})

        # Base score based on importance
        score += result.get("importance", 0) * 100

        # Bonus if the city is in the address
        city_in_address = (
            address.get("city", "").lower() == city_lower
            or address.get("town", "").lower() == city_lower
            or address.get("village", "").lower() == city_lower
        )
        if city_in_address:
            score += 50

        # Bonus if the name is in the display_name
        if name_lower in display_name:
            score += 30

        # Bonus for lower place_rank (more specific)
        place_rank = result.get("place_rank", 999)
        score += max(0, 30 - place_rank)

        # Penalty for generic places
        if result.get("class") == "place" and result.get("type") in [
            "city",
            "town",
            "village",
        ]:
            score -= 20

        scored_results.append((score, result))

    # Sort results by score, highest first
    scored_results.sort(key=lambda x: x[0], reverse=True)

    print(f"Results found: {len(results)}")
    for i, (score, result) in enumerate(scored_results[:3]):
        print(f"  {i + 1}. Score: {score:.1f} - {result.get('display_name', '')[:80]}")

    return scored_results[0][1] if scored_results else results[0]


def create_day_map(events_with_location, stay, next_day_stay):
    """
    Create a map for a given day with events, stay, and next day stay.
    """
    # Check if there's anything to show on the map
    if not events_with_location and (not stay or not stay.latitude):
        return None

    # Aggregate event locations
    bounds = events_with_location.aggregate(
        min_lat=Min("latitude"),
        max_lat=Max("latitude"),
        min_lon=Min("longitude"),
        max_lon=Max("longitude"),
    )

    # Include stay location in bounds calculation
    if stay and stay.latitude and stay.longitude:
        bounds["min_lat"] = min(bounds["min_lat"] or stay.latitude, stay.latitude)
        bounds["max_lat"] = max(bounds["max_lat"] or stay.latitude, stay.latitude)
        bounds["min_lon"] = min(bounds["min_lon"] or stay.longitude, stay.longitude)
        bounds["max_lon"] = max(bounds["max_lon"] or stay.longitude, stay.longitude)

    # Include next day's stay in bounds calculation if different
    if next_day_stay and next_day_stay != stay and next_day_stay.latitude:
        bounds["min_lat"] = min(
            bounds["min_lat"] or next_day_stay.latitude, next_day_stay.latitude
        )
        bounds["max_lat"] = max(
            bounds["max_lat"] or next_day_stay.latitude, next_day_stay.latitude
        )
        bounds["min_lon"] = min(
            bounds["min_lon"] or next_day_stay.longitude, next_day_stay.longitude
        )
        bounds["max_lon"] = max(
            bounds["max_lon"] or next_day_stay.longitude, next_day_stay.longitude
        )

    # Create a map
    m = folium.Map(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains="abcd",
        width="100%",
        height="100%",
    )
    # Add a bias
    bias = 0.005
    fit_bounds_payload = [
        [bounds["min_lat"] - bias, bounds["min_lon"] - bias],
        [bounds["max_lat"] + bias, bounds["max_lon"] + bias],
    ]
    m.fit_bounds(fit_bounds_payload)

    # Add specific icons
    experience_icon = folium.Icon(prefix="fa", color="green", icon="images")
    meal_icon = folium.Icon(prefix="fa", color="orange", icon="utensils")
    stay_icon = folium.Icon(prefix="fa", color="blue", icon="bed")

    # Add markers for each event
    for event in events_with_location:
        icon = experience_icon if event.category == 2 else meal_icon
        folium.Marker(
            [event.latitude, event.longitude],
            popup=event.name,
            tooltip=event.name,
            icon=icon,
        ).add_to(m)

    # Add marker for the stay
    if stay and stay.latitude and stay.longitude:
        folium.Marker(
            [stay.latitude, stay.longitude],
            popup=stay.name,
            tooltip=stay.name,
            icon=stay_icon,
        ).add_to(m)

    # Add marker for the next day's stay if it's different
    if (
        next_day_stay
        and next_day_stay != stay
        and next_day_stay.latitude
        and next_day_stay.longitude
    ):
        folium.Marker(
            [next_day_stay.latitude, next_day_stay.longitude],
            popup=next_day_stay.name,
            tooltip=f"Next day: {next_day_stay.name}",
            icon=stay_icon,
        ).add_to(m)

    return m._repr_html_()
