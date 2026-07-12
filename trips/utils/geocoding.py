import hashlib
import logging
import time

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

logger = logging.getLogger(__name__)


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
        logger.error(f"Error geocoding: {e}")

    return []


def geocode_trip_destination(trip):
    """
    Geocode trip.destination via Nominatim and update all main-destination days
    (days whose destination matches trip.destination or is blank) with
    destination_latitude/destination_longitude.
    Returns (lat, lon) or (None, None) if geocoding fails.
    """
    results = geocode_city(trip.destination)
    if not results:
        return None, None
    best = results[0]
    lat, lon = best["lat"], best["lon"]
    from trips.models import Day

    Day.objects.filter(trip=trip).filter(
        Q(destination="") | Q(destination=trip.destination)
    ).update(destination_latitude=lat, destination_longitude=lon)
    return lat, lon


def geocode_city(query):
    """Search for a city/destination using Nominatim. Returns a list of city results with name, country, lat, lon."""
    if not query:
        return []

    cache_key = f"geocode_city_{query.strip().lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    rate_limit_check()
    time.sleep(1)

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query.strip(),
        "format": "json",
        "limit": 5,
        "addressdetails": 1,
        "featuretype": "city",
    }
    headers = {"User-Agent": "OrganizeIt-Geocoding"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            results = response.json()
            city_list = []
            for result in results:
                addr = result.get("address", {})
                city_name = (
                    result.get("name")
                    or addr.get("city")
                    or addr.get("town")
                    or addr.get("village")
                    or ""
                )
                country = addr.get("country", "")
                city_list.append(
                    {
                        "name": city_name,
                        "country": country,
                        "lat": float(result.get("lat", 0)),
                        "lon": float(result.get("lon", 0)),
                        "importance": result.get("importance", 0),
                    }
                )
            city_list.sort(key=lambda x: x["importance"], reverse=True)
            seen = set()
            deduped = []
            for item in city_list:
                key = (item["name"].lower(), item["country"].lower())
                if key not in seen:
                    seen.add(key)
                    deduped.append(item)
            cache.set(cache_key, deduped, 3600)
            return deduped
    except Exception as e:
        logger.error(f"Error geocoding city: {e}")

    return []


def fetch_route(lat1, lng1, lat2, lng2):
    """Call Mapbox Directions API. Returns (duration_minutes, distance_km) or None on failure."""
    url = (
        f"https://api.mapbox.com/directions/v5/mapbox/driving/"
        f"{lng1},{lat1};{lng2},{lat2}"
    )
    try:
        resp = requests.get(
            url, params={"access_token": settings.MAPBOX_ACCESS_TOKEN}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(
            f"Mapbox Directions API error ({lat1},{lng1})→({lat2},{lng2}): {e}"
        )
        return None
    if data.get("routes"):
        route = data["routes"][0]
        return round(route["duration"] / 60), round(route["distance"] / 1000)
    return None


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

    return scored_results[0][1] if scored_results else results[0]


def convert_google_opening_hours(google_hours):
    if not google_hours or "periods" not in google_hours:
        return None

    custom_hours = {}
    day_map = {
        0: "sunday",
        1: "monday",
        2: "tuesday",
        3: "wednesday",
        4: "thursday",
        5: "friday",
        6: "saturday",
    }

    for period in google_hours.get("periods", []):
        if "open" in period and "close" in period:
            day_of_week_int = period["open"]["day"]
            day_name = day_map.get(day_of_week_int)
            if day_name:
                open_minute = period["open"].get("minute", 0)
                close_minute = period["close"].get("minute", 0)
                open_time = f"{period['open']['hour']:02d}:{open_minute:02d}"
                close_time = f"{period['close']['hour']:02d}:{close_minute:02d}"

                custom_hours[day_name] = {
                    "open": open_time,
                    "close": close_time,
                }
    return custom_hours if custom_hours else None
