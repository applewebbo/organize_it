import hashlib
import logging
import time
from io import BytesIO

import folium
import requests
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import BooleanField, Case, F, Max, Min, Prefetch, Q, When, Window
from django.db.models.functions import Lag, Lead
from django.http import Http404
from PIL import Image

from accounts.models import Profile
from trips.models import Event, Trip

logger = logging.getLogger(__name__)


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
    """Get the trips for the home page with favourite trip and latest/others"""
    profile = Profile.objects.get(user=user)
    fav_trip = profile.fav_trip

    # If there's a favorite trip, fetch it with full prefetch for detail view
    if fav_trip:
        fav_trip = (
            Trip.objects.prefetch_related(
                Prefetch(
                    "days__events",
                    queryset=annotate_event_overlaps(Event.objects.all()).order_by(
                        "start_time"
                    ),
                ),
                "days__stay",
            )
            .select_related("author")
            .get(pk=fav_trip.pk)
        )
        unpaired_events = fav_trip.all_events.filter(day__isnull=True)
    else:
        unpaired_events = None

    # Base queryset: all user trips excluding archived
    base_qs = Trip.objects.filter(author=user).exclude(status=Trip.Status.ARCHIVED)
    if fav_trip:
        base_qs = base_qs.exclude(pk=fav_trip.pk)

    # Determine "latest trip" with smart logic only if NO favorite
    latest_trip = None
    if not fav_trip and base_qs.exists():
        # Queryset with prefetch for the detail view
        latest_qs = base_qs.prefetch_related(
            Prefetch(
                "days__events",
                queryset=annotate_event_overlaps(Event.objects.all()).order_by(
                    "start_time"
                ),
            ),
            "days__stay",
        ).select_related("author")

        # Priority: IN_PROGRESS > IMPENDING (by start_date) > others
        latest_trip = (
            latest_qs.filter(status=Trip.Status.IN_PROGRESS).first()
            or latest_qs.filter(status=Trip.Status.IMPENDING)
            .order_by("start_date")
            .first()
            or latest_qs.order_by("status", "start_date").first()
        )

        unpaired_events = latest_trip.all_events.filter(day__isnull=True)
        other_trips = base_qs.exclude(pk=latest_trip.pk).order_by(
            "status", "start_date"
        )
    else:
        other_trips = base_qs.order_by("status", "start_date")

    return {
        "fav_trip": fav_trip,
        "latest_trip": latest_trip,
        "other_trips": other_trips,
        "unpaired_events": unpaired_events,
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


def get_event_instance(event):
    """
    Get the specific event instance based on its category.
    """
    if event.category == 1:  # Transport
        return event.transport
    elif event.category == 2:  # Experience
        return event.experience
    elif event.category == 3:  # Meal
        return event.meal
    else:
        raise Http404("Invalid event category")
