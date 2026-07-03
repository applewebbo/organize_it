import csv
import hashlib
import logging
import time
from io import BytesIO
from pathlib import Path

import folium
import requests
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Max, Min, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from PIL import Image

from accounts.models import get_profile
from trips.models import Event, Experience, MainTransfer, Meal, Stay, Trip


def get_trip_stages(trip):
    """
    Return destination stages for a trip.
    Main stage (trip.destination) always first; custom stages follow.
    Each stage: {"destination": str, "days": [Day, ...], "is_main": bool}
    Days with blank destination are treated as belonging to the main stage.
    """
    days = list(trip.days.order_by("number"))
    main_dest = trip.destination
    groups = {}
    for day in days:
        key = day.destination if day.destination else main_dest
        groups.setdefault(key, []).append(day)

    main_days = groups.pop(main_dest, None)
    result = []
    for dest, dest_days in groups.items():
        result.append({"destination": dest, "days": dest_days, "is_main": False})
    if main_days is not None:
        result.append({"destination": main_dest, "days": main_days, "is_main": True})
    elif not result:
        result.append({"destination": main_dest, "days": [], "is_main": True})
    result.sort(key=lambda s: s["days"][0].date if s["days"] else trip.start_date)
    return result


def group_unpaired_events_by_stage(stages, unpaired_events):
    """
    Group unpaired events by stage destination.
    Returns list of dicts: [{"destination": str|None, "events": [...], "is_main": bool}]
    Events whose city matches no stage go into a None-destination group.
    Only groups with at least one event are returned.
    """
    events_list = list(unpaired_events)
    stage_dests = {s["destination"] for s in stages}
    groups = []
    for stage in stages:
        stage_events = [e for e in events_list if e.city == stage["destination"]]
        if stage_events:
            groups.append(
                {
                    "destination": stage["destination"],
                    "events": stage_events,
                    "is_main": stage["is_main"],
                }
            )
    no_stage_events = [
        e for e in events_list if not e.city or e.city not in stage_dests
    ]
    if no_stage_events:
        groups.append(
            {"destination": None, "events": no_stage_events, "is_main": False}
        )
    return groups


def group_days_by_destination(days):
    """
    Group an ordered list of Day objects into consecutive destination blocks.
    Returns a list of dicts:
      [{"destination": str, "days": [Day, ...],
        "next_destination": str|None,
        "transfer_duration": int|None,
        "transfer_distance": int|None}, ...]
    Returns None if all days share the same destination (flat layout).
    """
    day_list = list(days)
    if not day_list:
        return None
    destinations = {d.destination for d in day_list}
    if len(destinations) <= 1:
        return None
    groups = []
    for day in day_list:
        if groups and groups[-1]["destination"] == day.destination:
            groups[-1]["days"].append(day)
        else:
            groups.append({"destination": day.destination, "days": [day]})

    for i, group in enumerate(groups):
        if i < len(groups) - 1:
            next_group = groups[i + 1]
            first_day_of_next = next_group["days"][0]
            group["next_destination"] = next_group["destination"]
            group["transfer_duration"] = first_day_of_next.transfer_duration_from_prev
            group["transfer_distance"] = first_day_of_next.transfer_distance_from_prev
            group["last_day_pk"] = first_day_of_next.pk
        else:
            group["next_destination"] = None
            group["transfer_duration"] = None
            group["transfer_distance"] = None
            group["last_day_pk"] = None
    return groups


def accessible_trips_qs(user):
    """Return queryset of trips where user is author or collaborator."""
    return Trip.objects.filter(Q(author=user) | Q(collaborators=user)).distinct()


def editable_trips_qs(user):
    """Return queryset of trips where user is author or collaborator with can_edit=True."""
    return Trip.objects.filter(
        Q(author=user) | Q(collaborations__user=user, collaborations__can_edit=True)
    ).distinct()


def get_trip_or_404(pk, user):
    """Return Trip if user is author or collaborator, else 404."""
    return get_object_or_404(accessible_trips_qs(user), pk=pk)


def get_trip_for_owner_or_404(pk, user):
    """Return Trip if user is the owner (author), else 404."""
    return get_object_or_404(Trip, pk=pk, author=user)


def get_trip_for_editor_or_404(pk, user):
    """Return Trip if user is author or collaborator with can_edit=True, else 404."""
    return get_object_or_404(editable_trips_qs(user), pk=pk)


logger = logging.getLogger(__name__)


def get_flight_origin_icao(transfer):
    """Return ICAO code for origin airport of a flight transfer, or empty string."""
    if transfer and transfer.type == MainTransfer.Type.PLANE and transfer.origin_code:
        airport = get_airport_by_iata(transfer.origin_code)
        return airport.get("icao_code", "") if airport else ""
    return ""


def get_trips(user):
    """Get the trips for the home page with favourite trip and latest/others"""
    profile = get_profile(user)
    fav_trip = profile.fav_trip

    # Check user preference for default view
    default_view = profile.default_map_view
    show_map = default_view == "map"

    # If there's a favorite trip, fetch it with full prefetch for detail view
    if fav_trip:
        fav_trip = (
            Trip.objects.prefetch_related(
                Prefetch(
                    "days__events",
                    queryset=Event.objects.select_related(
                        "experience", "meal"
                    ).order_by("order", "pk"),
                ),
                Prefetch(
                    "days__stay",
                    queryset=Stay.objects.select_related("author"),
                ),
                "main_transfers",
            )
            .select_related("author")
            .get(pk=fav_trip.pk)
        )
        unpaired_events = fav_trip.all_events.filter(day__isnull=True)
    else:
        unpaired_events = None

    # Base queryset: owned + collaborated trips excluding archived
    base_qs = (
        Trip.objects.filter(Q(author=user) | Q(collaborators=user))
        .exclude(status=Trip.Status.ARCHIVED)
        .distinct()
    )
    if fav_trip:
        base_qs = base_qs.exclude(pk=fav_trip.pk)

    # Determine "latest trip" with smart logic only if NO favorite
    latest_trip = None
    if not fav_trip and base_qs.exists():
        # Find the trip ID first without heavy prefetches
        # Priority: IN_PROGRESS > IMPENDING (by start_date) > others
        latest_trip = (
            base_qs.filter(status=Trip.Status.IN_PROGRESS).first()
            or base_qs.filter(status=Trip.Status.IMPENDING)
            .order_by("start_date")
            .first()
            or base_qs.order_by("status", "start_date").first()
        )

        # Now fetch only the selected trip with all related data
        latest_trip = (
            Trip.objects.prefetch_related(
                Prefetch(
                    "days__events",
                    queryset=Event.objects.select_related(
                        "experience", "meal"
                    ).order_by("order", "pk"),
                ),
                Prefetch(
                    "days__stay",
                    queryset=Stay.objects.select_related("author"),
                ),
                "main_transfers",
            )
            .select_related("author")
            .get(pk=latest_trip.pk)
        )

        unpaired_events = latest_trip.all_events.filter(day__isnull=True)
        other_trips = base_qs.exclude(pk=latest_trip.pk).order_by(
            "status", "start_date"
        )
    else:
        other_trips = base_qs.order_by("status", "start_date")

    featured_trip = fav_trip or latest_trip
    arrival_transfer = None
    departure_transfer = None
    stays = None
    if featured_trip:
        for t in featured_trip.main_transfers.all():
            if t.direction == 1:
                arrival_transfer = t
            else:
                departure_transfer = t
        stays = (
            Stay.objects.filter(days__trip=featured_trip)
            .annotate(first_day_date=Min("days__date"), last_day_date=Max("days__date"))
            .distinct()
            .order_by("first_day_date")
        )

    # Day is ordered by "number" by default, so reuse the prefetched days
    featured_days = list(featured_trip.days.all()) if featured_trip else []
    day_groups = group_days_by_destination(featured_days) if featured_trip else None

    first_day = featured_days[0] if featured_days else None
    last_day = featured_days[-1] if featured_days else None

    return {
        "fav_trip": fav_trip,
        "latest_trip": latest_trip,
        "other_trips": other_trips,
        "unpaired_events": unpaired_events,
        "stays": stays,
        "show_map": show_map,
        "arrival_transfer": arrival_transfer,
        "departure_transfer": departure_transfer,
        "both_transfers_exist": arrival_transfer is not None
        and departure_transfer is not None,
        "arrival_origin_icao": get_flight_origin_icao(arrival_transfer),
        "departure_origin_icao": get_flight_origin_icao(departure_transfer),
        "day_groups": day_groups,
        "show_transfer_info": profile.show_transfer_info,
        "show_weather": profile.show_weather,
        "ai_suggestions_enabled": profile.ai_suggestions_enabled,
        "from_home_duration": first_day.transfer_duration_from_prev
        if first_day and not arrival_transfer
        else None,
        "from_home_distance": first_day.transfer_distance_from_prev
        if first_day and not arrival_transfer
        else None,
        "from_home_destination": (first_day.destination or featured_trip.destination)
        if first_day and not arrival_transfer
        else None,
        "to_home_duration": last_day.transfer_to_home_duration
        if last_day and not departure_transfer
        else None,
        "to_home_distance": last_day.transfer_to_home_distance
        if last_day and not departure_transfer
        else None,
        "to_home_destination": (last_day.destination or featured_trip.destination)
        if last_day and not departure_transfer
        else None,
    }


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


def search_unsplash_photos(query, per_page=3, orientation="landscape"):
    """
    Search Unsplash for photos with caching.

    Args:
        query: Search query (typically trip destination)
        per_page: Number of results (default 3 for UI)
        orientation: Photo orientation (default 'landscape')

    Returns:
        List of photo dicts or None on error
    """
    from django.conf import settings

    # Generate cache key
    cache_data = f"unsplash_{query}_{per_page}_{orientation}"
    cache_key = hashlib.md5(cache_data.encode(), usedforsecurity=False).hexdigest()

    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Unsplash cache hit for query: {query}")
        return cached_result

    # Check API key
    api_key = settings.UNSPLASH_ACCESS_KEY
    if not api_key:
        logger.error("Unsplash API key not configured")
        return None

    # API request
    try:
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": per_page, "orientation": orientation},
            headers={"Authorization": f"Client-ID {api_key}", "Accept-Version": "v1"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        # Extract relevant fields
        photos = []
        for result in data.get("results", []):
            photos.append(
                {
                    "id": result["id"],
                    "urls": {
                        "regular": result["urls"]["regular"],
                        "small": result["urls"]["small"],
                        "thumb": result["urls"]["thumb"],
                    },
                    "user": {
                        "name": result["user"]["name"],
                        "username": result["user"]["username"],
                        "profile": result["user"]["links"]["html"],
                    },
                    "links": {
                        "html": result["links"]["html"],
                        "download_location": result["links"]["download_location"],
                    },
                    "alt_description": result.get("alt_description", ""),
                }
            )

        # Cache for 6 hours (21600 seconds)
        cache.set(cache_key, photos, 21600)
        logger.info(f"Unsplash search successful: {len(photos)} results for '{query}'")
        return photos

    except requests.exceptions.Timeout:
        logger.error("Unsplash API timeout")
    except requests.RequestException as e:
        logger.error(f"Unsplash API error: {e}")

    return None


def download_unsplash_photo(photo_data):
    """
    Download photo from Unsplash and return file content.
    Also triggers Unsplash download tracking (TOS requirement).

    Args:
        photo_data: Photo dict from search_unsplash_photos

    Returns:
        Tuple of (image_content, metadata_dict) or (None, None)
    """
    from django.conf import settings

    api_key = settings.UNSPLASH_ACCESS_KEY
    if not api_key:
        return None, None

    try:
        # 1. Trigger download tracking (Unsplash TOS requirement)
        download_location = photo_data["links"]["download_location"]
        requests.get(
            download_location,
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=5,
        )

        # 2. Download the actual image
        image_url = photo_data["urls"]["regular"]
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # 3. Prepare metadata
        metadata = {
            "source": "unsplash",
            "unsplash_id": photo_data["id"],
            "photographer": photo_data["user"]["name"],
            "photographer_url": photo_data["user"]["profile"],
            "photo_url": photo_data["links"]["html"],
            "download_location": download_location,
        }

        logger.info(f"Downloaded Unsplash photo: {photo_data['id']}")
        return response.content, metadata

    except requests.RequestException as e:
        logger.error(f"Failed to download Unsplash photo: {e}")
        return None, None


def process_trip_image(image_file, max_size_mb=2):
    """
    Process uploaded image: validate size, resize if needed, ensure landscape.

    Args:
        image_file: UploadedFile or bytes
        max_size_mb: Maximum file size in MB

    Returns:
        Processed InMemoryUploadedFile or None if invalid
    """
    try:
        # Handle bytes vs UploadedFile
        if isinstance(image_file, bytes):
            img = Image.open(BytesIO(image_file))
            original_name = "unsplash_photo.jpg"
        else:
            img = Image.open(image_file)
            original_name = image_file.name

            # Check file size
            image_file.seek(0, 2)  # Seek to end
            size_mb = image_file.size / (1024 * 1024)
            image_file.seek(0)  # Reset

            if size_mb > max_size_mb:
                logger.warning(f"Image too large: {size_mb:.2f}MB > {max_size_mb}MB")
                # Continue to resize instead of rejecting

        # Convert to RGB if needed (handle RGBA, grayscale, etc)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Ensure landscape orientation (width > height)
        width, height = img.size
        if height > width:
            # Rotate to landscape
            img = img.rotate(90, expand=True)
            width, height = img.size

        # Calculate target dimensions maintaining aspect ratio
        # Target max dimensions: 1200x800 for landscape
        target_width = 1200
        target_height = 800
        aspect_ratio = width / height

        if aspect_ratio > (target_width / target_height):
            # Image is wider than target
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            # Image is taller than target
            new_height = target_height
            new_width = int(target_height * aspect_ratio)

        # Resize if larger than target
        if width > new_width or height > new_height:
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(
                f"Resized image from {width}x{height} to {new_width}x{new_height}"
            )

        # Save to BytesIO
        output = BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        output.seek(0)

        # Create InMemoryUploadedFile
        processed_file = InMemoryUploadedFile(
            output,
            "ImageField",
            original_name,
            "image/jpeg",
            output.getbuffer().nbytes,
            None,
        )

        return processed_file

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return None


DAY_COLORS = [
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#06b6d4",
    "#8b5cf6",
    "#ec4899",
    "#14b8a6",
    "#f43f5e",
    "#6366f1",
]
STAY_ICON_COLOR = "gray"


def create_trip_map(days_with_events, unassigned_events):
    """
    Create a unified Folium map for all trip days.
    Each day is a FeatureGroup with a distinct color; LayerControl allows toggling.
    Stays use a neutral gray icon. Returns the HTML string (iframe srcdoc).
    """
    all_points = []

    # Collect any point to check if map is worth creating
    for day_data in days_with_events:
        stay = day_data["stay"]
        if stay and stay.latitude:
            all_points.append((stay.latitude, stay.longitude))
        for ev in day_data["events"]:
            if ev.latitude and ev.longitude:
                all_points.append((ev.latitude, ev.longitude))
    for ev in unassigned_events:
        if ev.latitude and ev.longitude:
            all_points.append((ev.latitude, ev.longitude))

    if not all_points:
        return None

    center = [
        sum(p[0] for p in all_points) / len(all_points),
        sum(p[1] for p in all_points) / len(all_points),
    ]

    m = folium.Map(
        location=center, zoom_start=12, tiles=None, width="100%", height="500px"
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        name="Mappa",
        control=False,
    ).add_to(m)

    seen_stay_pks = set()
    fg_stays = folium.FeatureGroup(
        name='<span style="display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:-1px;background:#6b7280;margin-right:5px"></span>Soggiorni'
    )

    for idx, day_data in enumerate(days_with_events, start=1):
        day = day_data["day"]
        color = DAY_COLORS[(idx - 1) % len(DAY_COLORS)]
        fg = folium.FeatureGroup(
            name=f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:-1px;background:{color};margin-right:5px"></span>Giorno {idx} — {day.date.strftime("%d %b")}'
        )

        stay = day_data["stay"]
        if stay and stay.pk not in seen_stay_pks and stay.latitude and stay.longitude:
            seen_stay_pks.add(stay.pk)
            folium.Marker(
                [stay.latitude, stay.longitude],
                popup=stay.name,
                tooltip=stay.name,
                icon=folium.DivIcon(
                    html='<div style="background:#6b7280;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.8);box-shadow:0 2px 5px rgba(0,0,0,0.35)"><i class="fa fa-bed" style="color:white;font-size:13px"></i></div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    popup_anchor=(0, -15),
                ),
            ).add_to(fg_stays)

        for ev in day_data["events"]:
            if not (ev.latitude and ev.longitude):
                continue
            icon_name = "cutlery" if ev.category == 3 else "map-marker"
            folium.Marker(
                [ev.latitude, ev.longitude],
                popup=ev.name,
                tooltip=ev.name,
                icon=folium.DivIcon(
                    html=f'<div style="background:{color};width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.8);box-shadow:0 2px 5px rgba(0,0,0,0.35)"><i class="fa fa-{icon_name}" style="color:white;font-size:13px"></i></div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    popup_anchor=(0, -15),
                ),
            ).add_to(fg)

        fg.add_to(m)

    if seen_stay_pks:
        fg_stays.add_to(m)

    fg_unassigned = folium.FeatureGroup(name="Senza giorno")
    has_unassigned = False
    for ev in unassigned_events:
        if not (ev.latitude and ev.longitude):
            continue
        folium.Marker(
            [ev.latitude, ev.longitude],
            popup=ev.name,
            tooltip=ev.name,
            icon=folium.DivIcon(
                html='<div style="background:#9ca3af;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.8);box-shadow:0 2px 5px rgba(0,0,0,0.35)"><i class="fa fa-map-marker" style="color:white;font-size:13px"></i></div>',
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                popup_anchor=(0, -15),
            ),
        ).add_to(fg_unassigned)
        has_unassigned = True
    if has_unassigned:
        fg_unassigned.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds(
        [
            [min(p[0] for p in all_points), min(p[1] for p in all_points)],
            [max(p[0] for p in all_points), max(p[1] for p in all_points)],
        ],
        padding=[30, 30],
    )

    return m._repr_html_()


def create_day_map(events_with_location, stay, next_day_stay, day=None):
    """
    Create a map for a given day with events, stay, and next day stay.

    Args:
        events_with_location: QuerySet of events with coordinates
        stay: Stay object for the current day
        next_day_stay: Stay object for the next day (if different)
        day: Optional Day object (for main transfer integration)
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

    # Include main transfers if this is the first or last day
    main_transfer_markers = []
    if day:
        trip = day.trip
        total_days = trip.days.count()

        # First day: include ARRIVAL transfer destination
        if day.number == 1:
            arrival = trip.main_transfers.filter(
                direction=MainTransfer.Direction.ARRIVAL
            ).first()

            if (
                arrival
                and arrival.destination_latitude
                and arrival.destination_longitude
            ):
                # Include in bounds
                bounds["min_lat"] = min(
                    bounds["min_lat"] or arrival.destination_latitude,
                    arrival.destination_latitude,
                )
                bounds["max_lat"] = max(
                    bounds["max_lat"] or arrival.destination_latitude,
                    arrival.destination_latitude,
                )
                bounds["min_lon"] = min(
                    bounds["min_lon"] or arrival.destination_longitude,
                    arrival.destination_longitude,
                )
                bounds["max_lon"] = max(
                    bounds["max_lon"] or arrival.destination_longitude,
                    arrival.destination_longitude,
                )

                # Store for marker creation later
                main_transfer_markers.append(
                    {
                        "lat": arrival.destination_latitude,
                        "lon": arrival.destination_longitude,
                        "name": arrival.destination_name,
                        "type": "arrival",
                        "transport_type": arrival.type,
                    }
                )

        # Last day: include DEPARTURE transfer origin
        if day.number == total_days:
            departure = trip.main_transfers.filter(
                direction=MainTransfer.Direction.DEPARTURE
            ).first()

            if departure and departure.origin_latitude and departure.origin_longitude:
                # Include in bounds
                bounds["min_lat"] = min(
                    bounds["min_lat"] or departure.origin_latitude,
                    departure.origin_latitude,
                )
                bounds["max_lat"] = max(
                    bounds["max_lat"] or departure.origin_latitude,
                    departure.origin_latitude,
                )
                bounds["min_lon"] = min(
                    bounds["min_lon"] or departure.origin_longitude,
                    departure.origin_longitude,
                )
                bounds["max_lon"] = max(
                    bounds["max_lon"] or departure.origin_longitude,
                    departure.origin_longitude,
                )

                # Store for marker creation later
                main_transfer_markers.append(
                    {
                        "lat": departure.origin_latitude,
                        "lon": departure.origin_longitude,
                        "name": departure.origin_name,
                        "type": "departure",
                        "transport_type": departure.type,
                    }
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

    # Add markers for main transfers (arrival/departure)
    for marker_data in main_transfer_markers:
        label = "Arrival" if marker_data["type"] == "arrival" else "Departure"

        # Choose icon based on transport type
        transport_type = marker_data.get("transport_type")
        if transport_type == MainTransfer.Type.PLANE:
            icon_name = "plane"
        elif transport_type == MainTransfer.Type.TRAIN:
            icon_name = "train"
        elif transport_type == MainTransfer.Type.CAR:
            icon_name = "car"
        else:  # OTHER
            icon_name = "person-walking"

        icon = folium.Icon(prefix="fa", color="red", icon=icon_name)

        folium.Marker(
            [marker_data["lat"], marker_data["lon"]],
            popup=f"{label}: {marker_data['name']}",
            tooltip=f"{label}: {marker_data['name']}",
            icon=icon,
        ).add_to(m)

    return m._repr_html_()


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


def build_categorized_event(category, **fields):
    """Build the proper STI child (Experience/Meal) for the given category.

    The map place-search and AI-suggestion accept flows must create a real
    Experience/Meal so every event has its STI child row; a plain ``Event``
    would break the event-detail modal (see get_event_instance).
    """
    model = {Event.Category.EXPERIENCE: Experience, Event.Category.MEAL: Meal}
    return model[category](**fields)


def get_event_instance(event):
    """
    Get the specific event instance based on its category.
    """
    if event.category == 2:  # Experience
        return event.experience
    elif event.category == 3:  # Meal
        return event.meal
    else:
        raise Http404("Invalid event category")


# Cache for CSV data (lazy loading)
_AIRPORTS_CACHE = None
_STATIONS_CACHE = None


def load_airports():
    """
    Load airports from CSV (with cache).
    Returns list of airport dicts with: iata_code, icao_code, name, city, latitude, longitude
    """
    global _AIRPORTS_CACHE

    if _AIRPORTS_CACHE is not None:
        return _AIRPORTS_CACHE

    airports = []
    csv_path = Path(settings.BASE_DIR) / "trips" / "data" / "airports_simple.csv"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            airports.append(
                {
                    "iata_code": row["iata_code"],
                    "icao_code": row.get("icao_code", ""),
                    "name": row["name"],
                    "city": row["city"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )

    _AIRPORTS_CACHE = airports
    return airports


def load_train_stations():
    """
    Load train stations from CSV (with cache).
    Returns list of station dicts with: id, name, country, latitude, longitude
    """
    global _STATIONS_CACHE

    if _STATIONS_CACHE is not None:
        return _STATIONS_CACHE

    stations = []
    csv_path = Path(settings.BASE_DIR) / "trips" / "data" / "stations_simplified.csv"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip stations without coordinates
            if not row.get("latitude") or not row.get("longitude"):
                continue

            try:
                stations.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "country": row["country"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                    }
                )
            except ValueError, KeyError:
                # Skip rows with invalid data
                continue

    _STATIONS_CACHE = stations
    return stations


def search_airports(query, limit=10):
    """
    Search airports by name, city, or IATA code.

    Args:
        query: Search text
        limit: Maximum number of results

    Returns:
        List of airports matching the query
    """
    airports = load_airports()
    query_lower = query.lower()

    results = []
    for airport in airports:
        if (
            query_lower in airport["iata_code"].lower()
            or query_lower in airport["name"].lower()
            or query_lower in airport["city"].lower()
        ):
            results.append(airport)
            if len(results) >= limit:
                break

    return results


def search_train_stations(query, limit=10):
    """
    Search train stations by name or country.

    Args:
        query: Search text
        limit: Maximum number of results

    Returns:
        List of stations matching the query
    """
    stations = load_train_stations()
    query_lower = query.lower()

    results = []
    for station in stations:
        if (
            query_lower in station["name"].lower()
            or query_lower in station["country"].lower()
        ):
            results.append(station)
            if len(results) >= limit:
                break

    return results


def get_airport_by_iata(iata_code):
    """
    Find airport by IATA code.

    Args:
        iata_code: IATA code (e.g., 'FCO')

    Returns:
        Airport dict or None if not found
    """
    airports = load_airports()
    for airport in airports:
        if airport["iata_code"].upper() == iata_code.upper():
            return airport
    return None


def get_station_by_id(station_id):
    """
    Find train station by ID.

    Args:
        station_id: Station ID as string

    Returns:
        Station dict or None if not found
    """
    stations = load_train_stations()
    for station in stations:
        if station["id"] == str(station_id):
            return station
    return None
