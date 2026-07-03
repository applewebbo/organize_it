import json
import logging
import math
import re
import urllib.parse

import geocoder
import requests
from django.conf import settings
from django.contrib import messages
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from accounts.models import get_profile
from suggestions.services import get_cached_suggestions
from trips.models import Day, Event, MainTransfer, Stay, Trip
from trips.services import GooglePlacesClient, GooglePlacesError
from trips.utils import (
    accessible_trips_qs,
    build_categorized_event,
    create_trip_map,
    editable_trips_qs,
    geocode_city,
    geocode_location,
    get_trip_stages,
    group_days_by_destination,
)

logger = logging.getLogger(__name__)


def _build_map_events_context(trip):
    """Return days_with_events and unassigned_events for the map events panel."""
    days = trip.days.prefetch_related(
        Prefetch(
            "events",
            queryset=Event.objects.filter(
                category__in=[Event.Category.EXPERIENCE, Event.Category.MEAL]
            ).order_by("order", "pk"),
        ),
        "stay",
    ).order_by("date")

    days_with_events = []
    for day in days:
        events = list(day.events.all())  # uses prefetch cache
        stay = day.stay if hasattr(day, "stay") and day.stay else None
        if events or stay:
            days_with_events.append({"day": day, "events": events, "stay": stay})
    unassigned_events = trip.all_events.filter(day__isnull=True).order_by("name")
    return days_with_events, unassigned_events


def _build_map_json(days_with_events, unassigned_events, trip):
    """
    Serialize all map items to a JSON-safe list for the Leaflet JS module.
    Each item has: kind, name, address, lat, lng, day_index (0=unassigned),
    stage (destination name the item belongs to, so the client can fit the map
    tightly to a stage's own markers).
    """
    items = []
    seen_stay_pks = set()

    for idx, day_data in enumerate(days_with_events, start=1):
        day = day_data["day"]
        stage = day.destination or trip.destination
        stay = day_data["stay"]
        if stay and stay.pk not in seen_stay_pks and stay.latitude and stay.longitude:
            seen_stay_pks.add(stay.pk)
            items.append(
                {
                    "kind": "stay",
                    "name": stay.name,
                    "address": stay.address,
                    "lat": stay.latitude,
                    "lng": stay.longitude,
                    "day_index": idx,
                    "stage": stage,
                }
            )
        for event in day_data["events"]:
            if event.latitude and event.longitude:
                items.append(
                    {
                        "kind": "meal" if event.category == 3 else "experience",
                        "name": event.name,
                        "address": event.address,
                        "lat": event.latitude,
                        "lng": event.longitude,
                        "day_index": idx,
                        "stage": stage,
                    }
                )

    for event in unassigned_events:
        if event.latitude and event.longitude:
            items.append(
                {
                    "kind": "meal" if event.category == 3 else "experience",
                    "name": event.name,
                    "address": event.address,
                    "lat": event.latitude,
                    "lng": event.longitude,
                    "day_index": 0,
                    "stage": None,
                }
            )

    return items


def _stage_points(stage):
    """Collect candidate [lat, lng] points that locate a stage.

    Prefers the days' own geocoded destination coords; when those are missing
    (older/imported stages never store them) it falls back to the real places
    planned in the stage — its stays and events — so every stage stays
    locatable on the map.
    """
    points = [
        (day.destination_latitude, day.destination_longitude)
        for day in stage["days"]
        if day.destination_latitude is not None
        and day.destination_longitude is not None
    ]
    if points:
        return points

    day_pks = [day.pk for day in stage["days"]]
    points += list(
        Stay.objects.filter(days__pk__in=day_pks)
        .exclude(latitude=None)
        .exclude(longitude=None)
        .values_list("latitude", "longitude")
        .distinct()
    )
    points += list(
        Event.objects.filter(
            day__pk__in=day_pks, latitude__isnull=False, longitude__isnull=False
        ).values_list("latitude", "longitude")
    )
    return points


def _build_stage_coords(trip, stages):
    """Map each stage's destination name to representative [lat, lng] coords.

    The main stage uses the trip's own destination coords when available;
    otherwise (and for custom stages) coords are averaged from the stage's
    days/places. Stages with no locatable point are omitted.
    """
    coords = {}
    for stage in stages:
        if (
            stage["is_main"]
            and trip.destination_latitude is not None
            and trip.destination_longitude is not None
        ):
            coords[stage["destination"]] = [
                trip.destination_latitude,
                trip.destination_longitude,
            ]
            continue
        points = _stage_points(stage)
        if points:
            coords[stage["destination"]] = [
                sum(p[0] for p in points) / len(points),
                sum(p[1] for p in points) / len(points),
            ]
    return coords


def trip_map(request, pk):
    """Unified interactive map for a trip: all events across all days + unassigned."""
    trip = get_object_or_404(
        Trip.objects.prefetch_related("collaborations"),
        pk=pk,
    )
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404

    days_with_events, unassigned_events = _build_map_events_context(trip)
    map_items = _build_map_json(days_with_events, unassigned_events, trip)
    stages = get_trip_stages(trip)
    has_cache = get_cached_suggestions(request.user, trip) is not None
    return TemplateResponse(
        request,
        "trips/trip-map.html",
        {
            "trip": trip,
            "days_with_events": days_with_events,
            "unassigned_events": unassigned_events,
            "map_items_json": json.dumps(map_items),
            "stage_coords_json": json.dumps(_build_stage_coords(trip, stages)),
            "stages": stages,
            "has_custom_stages": any(not s["is_main"] for s in stages),
            "has_cache": has_cache,
        },
    )


def trip_events_map(request, pk):
    """HTMX fragment: embedded Folium map for all trip events (trip-detail toggle)."""
    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404
    days_with_events, unassigned_events = _build_map_events_context(trip)
    trip_map_html = create_trip_map(days_with_events, unassigned_events)
    return TemplateResponse(
        request,
        "trips/includes/events-map-fragment.html",
        {
            "trip": trip,
            "map": trip_map_html,
        },
    )


def trip_events_list(request, pk):
    """HTMX fragment: days list for trip-detail events section (map→list toggle)."""
    trip = get_object_or_404(
        Trip.objects.prefetch_related(
            Prefetch(
                "days__events",
                queryset=Event.objects.all().order_by("order", "pk"),
            ),
            "days__stay",
        ),
        pk=pk,
    )
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404
    unpaired_events = trip.all_events.filter(day__isnull=True)
    day_groups = group_days_by_destination(trip.days.all())
    profile = get_profile(request.user)
    arrival_transfer = trip.main_transfers.filter(
        direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure_transfer = trip.main_transfers.filter(
        direction=MainTransfer.Direction.DEPARTURE
    ).first()
    first_day = trip.days.order_by("number").first()
    last_day = trip.days.order_by("number").last()
    return TemplateResponse(
        request,
        "trips/includes/events-list-fragment.html",
        {
            "trip": trip,
            "unpaired_events": unpaired_events,
            "day_groups": day_groups,
            "show_transfer_info": profile.show_transfer_info,
            "show_weather": profile.show_weather,
            "from_home_duration": first_day.transfer_duration_from_prev
            if first_day and not arrival_transfer
            else None,
            "from_home_distance": first_day.transfer_distance_from_prev
            if first_day and not arrival_transfer
            else None,
            "from_home_destination": (first_day.destination or trip.destination)
            if first_day and not arrival_transfer
            else None,
            "to_home_duration": last_day.transfer_to_home_duration
            if last_day and not departure_transfer
            else None,
            "to_home_distance": last_day.transfer_to_home_distance
            if last_day and not departure_transfer
            else None,
            "to_home_destination": (last_day.destination or trip.destination)
            if last_day and not departure_transfer
            else None,
        },
    )


def trip_destinations(request, trip_pk):
    """HTMX modal step 1: show current stages."""
    trip = get_object_or_404(
        accessible_trips_qs(request.user).prefetch_related("days"),
        pk=trip_pk,
    )
    stages = get_trip_stages(trip)
    return TemplateResponse(
        request,
        "trips/includes/trip-destinations-modal.html",
        {"trip": trip, "stages": stages},
    )


def create_stage(request, trip_pk):
    """HTMX modal step 2: form to create a new stage (GET) or save it (POST)."""
    trip = get_object_or_404(
        editable_trips_qs(request.user).prefetch_related("days"), pk=trip_pk
    )
    stages = get_trip_stages(trip)
    custom_day_pks = {
        day.pk for stage in stages if not stage["is_main"] for day in stage["days"]
    }

    if request.method == "POST":
        from django_q.tasks import async_task

        destination = request.POST.get("destination", "").strip()
        dest_lat = request.POST.get("destination_latitude", "").strip()
        dest_lon = request.POST.get("destination_longitude", "").strip()
        selected_pks = {int(pk) for pk in request.POST.getlist("days")}
        if destination and selected_pks:
            valid_pks = selected_pks - custom_day_pks
            update_fields = {"destination": destination}
            if dest_lat and dest_lon:
                try:
                    update_fields["destination_latitude"] = float(dest_lat)
                    update_fields["destination_longitude"] = float(dest_lon)
                except ValueError:
                    pass
            Day.objects.filter(pk__in=valid_pks, trip=trip).update(**update_fields)
            affected_numbers = list(
                Day.objects.filter(pk__in=valid_pks, trip=trip).values_list(
                    "number", flat=True
                )
            )
            if affected_numbers:
                min_number = min(affected_numbers)
                max_number = max(affected_numbers)
                # Recalculate transfer arriving at the first day of the new stage
                first_of_stage_pk = (
                    Day.objects.filter(trip=trip, number=min_number)
                    .values_list("pk", flat=True)
                    .first()
                )
                async_task("trips.tasks.calculate_day_transfer", first_of_stage_pk)
                # Recalculate transfer arriving at the first day of the stage after this one
                first_of_next = Day.objects.filter(
                    trip=trip, number=max_number + 1
                ).first()
                if first_of_next:
                    async_task("trips.tasks.calculate_day_transfer", first_of_next.pk)
        stages = get_trip_stages(trip)
        return TemplateResponse(
            request,
            "trips/includes/trip-destinations-modal.html",
            {"trip": trip, "stages": stages},
            headers={"HX-Trigger": "destinationModified"},
        )

    days = list(trip.days.order_by("number"))
    return TemplateResponse(
        request,
        "trips/includes/create-stage-modal.html",
        {"trip": trip, "days": days, "custom_day_pks": custom_day_pks},
    )


def delete_stage(request, trip_pk):
    """HTMX: delete a custom stage, reassign days to trip.destination, unpair events."""
    trip = get_object_or_404(
        editable_trips_qs(request.user).prefetch_related("days"), pk=trip_pk
    )
    if request.method == "POST":
        from django_q.tasks import async_task

        destination = request.POST.get("destination", "").strip()
        if destination and destination != trip.destination:
            stage_days = trip.days.filter(destination=destination)
            affected_numbers = sorted(stage_days.values_list("number", flat=True))
            for day in stage_days:
                day.events.update(day=None)
            # Reset coords and transfer data — no transfer exists anymore for these days
            stage_days.update(
                destination=trip.destination,
                destination_latitude=None,
                destination_longitude=None,
                transfer_duration_from_prev=None,
                transfer_distance_from_prev=None,
            )
            # Recalculate transfer for first day of stage after the deleted one
            first_of_next = Day.objects.filter(
                trip=trip, number=max(affected_numbers) + 1
            ).first()
            if first_of_next:
                async_task("trips.tasks.calculate_day_transfer", first_of_next.pk)
    stages = get_trip_stages(trip)
    return TemplateResponse(
        request,
        "trips/includes/trip-destinations-modal.html",
        {"trip": trip, "stages": stages},
        headers={"HX-Trigger": "destinationModified"},
    )


def update_day_destination(request, trip_pk, day_pk):
    """HTMX: update a single day's destination and return updated card."""
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    day = get_object_or_404(Day, pk=day_pk, trip=trip)
    if request.method == "POST":
        destination = request.POST.get("destination", "").strip()
        day.destination = destination
        day.save()
        return HttpResponse(
            status=204,
            headers={"HX-Trigger": "destinationModified"},
        )
    return TemplateResponse(
        request,
        "trips/includes/day-destination-card.html",
        {"day": day, "trip": trip},
    )


def select_day_for_event(request, pk, category):
    """HTMX: step-1 modal – choose a day before creating an experience or meal from map view."""
    if category not in ("experience", "meal"):
        raise Http404
    trip = get_object_or_404(Trip, pk=pk)
    if not editable_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404
    days = trip.days.order_by("date")
    return TemplateResponse(
        request,
        "trips/includes/day-selector.html",
        {"trip": trip, "days": days, "category": category},
    )


def geocode_address(request):
    """Geocode a location based on name and city using Nominatim OpenStreetMap and HTMX."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        city = request.POST.get("city", "").strip()

        if name and city:
            results = geocode_location(name, city)
            if results:
                return TemplateResponse(
                    request,
                    "trips/includes/address-results.html",
                    {
                        "addresses": results,
                        "found": True,
                    },
                )

        return TemplateResponse(
            request, "trips/includes/address-results.html", {"found": False}
        )

    return TemplateResponse(
        request, "trips/includes/address-results.html", {"found": False}
    )


def geocode_city_view(request):
    """HTMX: search for a city/destination using Nominatim and return a list of results."""
    if request.method == "POST":
        query = request.POST.get("destination", "").strip()
        if query:
            results = geocode_city(query)
            return TemplateResponse(
                request,
                "trips/includes/city-results.html",
                {"cities": results, "found": bool(results)},
            )
    return TemplateResponse(
        request, "trips/includes/city-results.html", {"found": False}
    )


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in meters between two lat/lng points."""
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _trip_location_bias(trip) -> tuple[float, float, float] | None:
    """
    Return (lat, lng, radius_meters) to bias Google Places search.
    Centroid of all trip events+stays; radius = max distance from centroid * 1.5
    (min 10 km, max 500 km). Falls back to geocoding trip.destination.
    """
    coords = list(
        Event.objects.filter(
            trip=trip, latitude__isnull=False, longitude__isnull=False
        ).values_list("latitude", "longitude")
    )
    stay_coords = list(
        Stay.objects.filter(
            days__trip=trip, latitude__isnull=False, longitude__isnull=False
        ).values_list("latitude", "longitude")
    )
    all_coords = coords + stay_coords
    if all_coords:
        clat = sum(c[0] for c in all_coords) / len(all_coords)
        clng = sum(c[1] for c in all_coords) / len(all_coords)
        max_dist = max(_haversine_m(clat, clng, c[0], c[1]) for c in all_coords)
        radius = min(max(max_dist * 1.5, 10_000), 50_000)
        return clat, clng, radius
    # Fallback: geocode the trip destination
    if trip.destination:
        g = geocoder.mapbox(trip.destination, key=settings.MAPBOX_ACCESS_TOKEN)
        if g.latlng:
            return g.latlng[0], g.latlng[1], 50_000
    return None


def _stage_location_bias(
    trip, stage_destination: str
) -> tuple[float, float, float] | None:
    """Return location_bias centred on events/days belonging to a specific stage."""
    coords = list(
        Event.objects.filter(
            trip=trip,
            day__destination=stage_destination,
            latitude__isnull=False,
            longitude__isnull=False,
        ).values_list("latitude", "longitude")
    )
    day_coords = list(
        trip.days.filter(destination=stage_destination)
        .exclude(destination_latitude=None)
        .values_list("destination_latitude", "destination_longitude")
    )
    all_coords = coords + day_coords
    if all_coords:
        clat = sum(c[0] for c in all_coords) / len(all_coords)
        clng = sum(c[1] for c in all_coords) / len(all_coords)
        max_dist = max(_haversine_m(clat, clng, c[0], c[1]) for c in all_coords)
        return clat, clng, min(max(max_dist * 1.5, 10_000), 50_000)
    # Fallback: geocode the stage destination name
    g = geocoder.mapbox(stage_destination, key=settings.MAPBOX_ACCESS_TOKEN)
    if g.latlng:
        return g.latlng[0], g.latlng[1], 50_000
    return _trip_location_bias(trip)


@require_http_methods(["POST"])
def map_search(request, pk):
    """HTMX endpoint: search Google Places and return results partial."""
    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404

    query = request.POST.get("query", "").strip()
    stage_destination = request.POST.get("stage_destination", "").strip()
    results = []
    error = None

    if query:
        client = GooglePlacesClient()
        location_bias = (
            _stage_location_bias(trip, stage_destination)
            if stage_destination
            else _trip_location_bias(trip)
        )
        try:
            results = client.search_text(query, location_bias=location_bias)
        except GooglePlacesError as e:
            error = str(e)

    return TemplateResponse(
        request,
        "trips/partials/map-search-results.html",
        {"results": results, "query": query, "error": error, "trip": trip},
    )


def _map_add_event(request, pk, category):
    """Shared logic: create an Event from Google Places data and return events panel."""
    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404

    name = request.POST.get("name", "").strip()
    address = request.POST.get("address", "").strip()
    place_id = request.POST.get("google_place_id", "").strip()
    lat = request.POST.get("lat", "").strip()
    lng = request.POST.get("lng", "").strip()

    if name:
        event = build_categorized_event(
            category,
            trip=trip,
            name=name,
            address=address,
            place_id=place_id,
            last_modified_by=request.user,
        )
        if lat and lng:
            try:
                event.latitude = float(lat)
                event.longitude = float(lng)
            except ValueError:
                pass
        event.save()
        messages.success(request, _("Event added to trip."))

    days_with_events, unassigned_events = _build_map_events_context(trip)
    return TemplateResponse(
        request,
        "trips/partials/map-events-panel.html",
        {
            "trip": trip,
            "days_with_events": days_with_events,
            "unassigned_events": unassigned_events,
        },
    )


@require_http_methods(["POST"])
def map_add_experience(request, pk):
    """HTMX: add an Experience from map search result."""
    return _map_add_event(request, pk, Event.Category.EXPERIENCE)


@require_http_methods(["POST"])
def map_add_meal(request, pk):
    """HTMX: add a Meal from map search result."""
    return _map_add_event(request, pk, Event.Category.MEAL)


@require_http_methods(["POST"])
def map_add_stay(request, pk):
    """HTMX: create a Stay (unassigned) from map search result."""
    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404

    name = request.POST.get("name", "").strip()
    address = request.POST.get("address", "").strip()
    place_id = request.POST.get("google_place_id", "").strip()
    lat = request.POST.get("lat", "").strip()
    lng = request.POST.get("lng", "").strip()

    if name:
        stay = Stay(
            name=name,
            address=address or "",
            place_id=place_id,
            author=request.user,
        )
        if lat and lng:
            try:
                stay.latitude = float(lat)
                stay.longitude = float(lng)
            except ValueError:
                pass
        stay.save()
        messages.success(request, _("Stay added to trip."))

    days_with_events, unassigned_events = _build_map_events_context(trip)
    return TemplateResponse(
        request,
        "trips/partials/map-events-panel.html",
        {
            "trip": trip,
            "days_with_events": days_with_events,
            "unassigned_events": unassigned_events,
        },
    )


_MAPS_PREFIXES = (
    "https://maps.app.goo.gl/",
    "https://goo.gl/maps/",
    "https://www.google.com/maps/",
    "https://maps.google.com/",
    "http://maps.google.com/",
)

_LODGING_TYPES = frozenset(
    {
        "lodging",
        "hotel",
        "motel",
        "hostel",
        "bed_and_breakfast",
        "extended_stay_hotel",
        "resort_hotel",
        "campground",
        "inn",
    }
)

_FOOD_TYPES = frozenset(
    {
        "restaurant",
        "cafe",
        "bar",
        "bakery",
        "meal_takeaway",
        "meal_delivery",
        "coffee_shop",
        "food",
        "fast_food_restaurant",
        "wine_bar",
        "pub",
    }
)


def _place_type_warning(form_type: str, place_types: list[str]) -> str | None:
    """Return a warning code if place types mismatch the form type, else None."""
    types_set = set(place_types)
    if form_type == "stay" and not (types_set & _LODGING_TYPES):
        return "stay_mismatch"
    if form_type == "meal" and not (types_set & _FOOD_TYPES):
        return "meal_mismatch"
    if form_type == "experience":
        if types_set & _LODGING_TYPES:
            return "experience_lodging"
        if types_set & _FOOD_TYPES:
            return "experience_food"
    return None


@require_http_methods(["POST"])
def resolve_maps_link(request):
    """HTMX: resolve a Google Maps link server-side and return place details for pre-fill."""
    url = request.POST.get("maps_link", "").strip()

    if not any(url.startswith(prefix) for prefix in _MAPS_PREFIXES):
        return TemplateResponse(
            request,
            "trips/includes/maps-link-prefill.html",
            {"error": True},
        )

    # Full Google Maps URLs don't need an HTTP round-trip
    is_short_link = url.startswith("https://maps.app.goo.gl/") or url.startswith(
        "https://goo.gl/maps/"
    )

    if is_short_link:
        try:
            resp = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            expanded_url = resp.url
            # Google may redirect to consent page — extract the actual Maps URL
            if "consent.google.com" in expanded_url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(expanded_url).query)
                if "continue" in qs:
                    expanded_url = urllib.parse.unquote(qs["continue"][0])
        except Exception:
            return TemplateResponse(
                request,
                "trips/includes/maps-link-prefill.html",
                {"error": True},
            )
    else:
        expanded_url = url

    place_id = None
    match = re.search(r"!1s(ChIJ[^!]+)", expanded_url)
    if match:
        place_id = match.group(1)
    else:
        # Fallback: extract name + coords from URL and do a text search
        name_match = re.search(r"/maps/place/([^/@]+)/?(?:@|$)", expanded_url)
        # Try !3d/!4d format first, then fall back to @lat,lng in the path
        lat_match = re.search(r"!3d(-?\d+\.\d+)", expanded_url)
        lng_match = re.search(r"!4d(-?\d+\.\d+)", expanded_url)
        if not (lat_match and lng_match):
            at_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", expanded_url)
            if at_match:
                lat_match = at_match
                lng_match = None  # use group(1)/group(2) from at_match below
                # Reassign to a unified variable for clarity
                lat_lng_from_at = (float(at_match.group(1)), float(at_match.group(2)))
            else:
                lat_lng_from_at = None
        else:
            lat_lng_from_at = None
        # Fallback for mobile share links that expand to ?q= format
        # e.g. https://maps.google.com/maps?q=Place+Name&ll=lat,lng
        # Excludes generic /search/ URLs which are not specific-place links.
        q_query = None
        if not name_match:
            parsed = urllib.parse.urlparse(expanded_url)
            qs_params = urllib.parse.parse_qs(parsed.query)
            q_values = qs_params.get("q", [])
            if q_values and q_values[0] and "/search" not in parsed.path:
                q_query = urllib.parse.unquote_plus(q_values[0])
                ll_values = qs_params.get("ll", [])
                if ll_values:
                    try:
                        ll_parts = ll_values[0].split(",")
                        lat_lng_from_at = (float(ll_parts[0]), float(ll_parts[1]))
                    except ValueError, IndexError:
                        lat_lng_from_at = None
                else:
                    lat_lng_from_at = None

        if name_match or q_query:
            if q_query:
                query = q_query
            else:
                query = urllib.parse.unquote_plus(name_match.group(1).replace("+", " "))
            location_bias = None
            if lat_lng_from_at:
                location_bias = (*lat_lng_from_at, 500)
            elif lat_match and lng_match:
                location_bias = (
                    float(lat_match.group(1)),
                    float(lng_match.group(1)),
                    500,
                )
            try:
                results = GooglePlacesClient().search_text(
                    query, max_results=1, location_bias=location_bias
                )
                if results:
                    place_id = results[0].place_id
            except GooglePlacesError:
                pass

    if not place_id:
        logger.warning("resolve_maps_link: no place_id found in %s", expanded_url[:200])
        return TemplateResponse(
            request,
            "trips/includes/maps-link-prefill.html",
            {"error": True},
        )

    try:
        details = GooglePlacesClient().get_full_place_details(place_id)
    except GooglePlacesError:
        return TemplateResponse(
            request,
            "trips/includes/maps-link-prefill.html",
            {"error": True},
        )

    form_type = request.POST.get("form_type", "")
    type_warning = _place_type_warning(form_type, details.types) if form_type else None

    place_data_json = json.dumps(
        {
            "name": details.name,
            "address": details.address,
            "city": details.city,
            "lat": details.lat,
            "lng": details.lng,
            "website": details.website,
            "phone": details.phone_number,
            "opening_hours": details.opening_hours,
        }
    )
    return TemplateResponse(
        request,
        "trips/includes/maps-link-prefill.html",
        {
            "found": True,
            "place_data_json": place_data_json,
            "type_warning": type_warning,
        },
    )
