import hashlib
import time
from datetime import date, timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from accounts.models import Profile
from trips.forms import (
    AddNoteToStayForm,
    EventChangeTimesForm,
    ExperienceForm,
    MealForm,
    NoteForm,
    StayForm,
    TransportForm,
    TripDateUpdateForm,
    TripForm,
)
from trips.models import Day, Event, Stay, Trip
from trips.utils import annotate_event_overlaps


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


def home(request):
    """Home page"""
    context = {}
    if request.user.is_authenticated:
        if Profile.objects.filter(user=request.user).exists():
            context = get_trips(request.user)
    return TemplateResponse(request, "trips/index.html", context)


@login_required
def trip_list(request):
    """List of all trips"""
    if request.htmx:
        template = "trips/trip-list.html#trip-list"
    else:
        template = "trips/trip-list.html"
    active_trips = Trip.objects.filter(author=request.user).exclude(status=5)
    archived_trips = Trip.objects.filter(author=request.user, status=5)
    context = {
        "active_trips": active_trips,
        "archived_trips": archived_trips,
    }
    return TemplateResponse(request, template, context)


@login_required
def trip_detail(request, pk):
    """
    Detail Page for the selected trip.
    Uses window functions to efficiently detect event overlaps within each day.
    """
    qs = Trip.objects.prefetch_related(
        Prefetch(
            "days__events",
            queryset=annotate_event_overlaps(Event.objects.all()).order_by(
                "start_time"
            ),
        ),
        "days__stay",
    ).select_related("author")

    trip = get_object_or_404(qs, pk=pk, author=request.user)
    unpaired_events = trip.all_events.filter(day__isnull=True)

    context = {"trip": trip, "unpaired_events": unpaired_events}
    if request.htmx:
        template = "trips/trip-detail.html#days"
    else:
        template = "trips/trip-detail.html"
    return TemplateResponse(request, template, context)


@login_required
def day_detail(request, pk):
    """
    Detail Page for the selected day.
    Uses window functions to efficiently detect event overlaps within the day.
    """
    qs = Day.objects.prefetch_related(
        Prefetch(
            "events",
            queryset=annotate_event_overlaps(Event.objects.all()).order_by(
                "start_time"
            ),
        ),
        "stay",
    ).select_related("trip__author")

    day = get_object_or_404(qs, pk=pk, trip__author=request.user)

    context = {
        "day": day,
    }
    return TemplateResponse(request, "trips/includes/day.html", context)


@login_required
def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.author = request.user
            trip.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{trip.title}</strong> added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm()
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-create.html", context)


@login_required
@require_http_methods(["DELETE"])
def trip_delete(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    trip.delete()
    messages.add_message(
        request,
        messages.ERROR,
        f"<strong>{trip.title}</strong> deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


@login_required
def trip_update(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    if request.method == "POST":
        form = TripForm(request.POST or None, instance=trip)
        if form.is_valid():
            trip = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{trip.title}</strong> updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        form = TripForm(request.POST, instance=trip)
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm(instance=trip)
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-create.html", context)


@login_required
def trip_archive(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    trip.status = 5
    trip.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        f"<strong>{trip.title}</strong> archived successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


@login_required
def trip_dates_update(request, pk):
    """
    Update the start and end dates of a trip.
    This view handles the form submission for updating trip dates and uses htmx to trigger a client-side event upon success.
    """
    trip = get_object_or_404(Trip, pk=pk, author=request.user)

    form = TripDateUpdateForm(request.POST or None, instance=trip)
    if form.is_valid():
        trip = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Dates updated successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/trip-dates-update.html", context)


@login_required
def add_transport(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    unpaired_experiences = Event.objects.filter(
        day__isnull=True, trip=day.trip, category=1
    )
    form = TransportForm(request.POST or None)
    if form.is_valid():
        transport = form.save(commit=False)
        transport.day = day
        transport.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Transport added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form, "day": day, "unpaired_experiences": unpaired_experiences}
    return TemplateResponse(request, "trips/transport-create.html", context)


@login_required
def add_experience(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    unpaired_experiences = Event.objects.filter(
        day__isnull=True, trip=day.trip, category=2
    )
    form = ExperienceForm(
        request.POST or None, include_city=True, initial={"city": day.trip.destination}
    )
    if form.is_valid():
        experience = form.save(commit=False)
        experience.day = day
        experience.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Experience added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form, "day": day, "unpaired_experiences": unpaired_experiences}
    return TemplateResponse(request, "trips/experience-create.html", context)


@login_required
def add_meal(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    unpaired_experiences = Event.objects.filter(
        day__isnull=True, trip=day.trip, category=3
    )
    form = MealForm(
        request.POST or None, include_city=True, initial={"city": day.trip.destination}
    )
    if form.is_valid():
        meal = form.save(commit=False)
        meal.day = day
        meal.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Meal added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form, "day": day, "unpaired_experiences": unpaired_experiences}
    return TemplateResponse(request, "trips/meal-create.html", context)


@login_required
def add_stay(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    trip = day.trip
    form = StayForm(
        trip,
        include_city=True,
        data=request.POST or None,
        initial={"apply_to_days": [day_id], "city": trip.destination},
    )
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form}
    return TemplateResponse(request, "trips/stay-create.html", context)


@login_required
def stay_detail(request, pk):
    stay = get_object_or_404(Stay, pk=pk)
    days = stay.days.order_by("date")
    last_day = days.last()
    first_stay_day = days.first()

    # Find the day before the first stay day in the trip's days
    first_day = (
        Day.objects.filter(
            trip=first_stay_day.trip, date=first_stay_day.date - timedelta(days=1)
        ).first()
        or first_stay_day
    )

    context = {
        "stay": stay,
        "first_day": first_day,
        "last_day": last_day,
    }
    return TemplateResponse(request, "trips/stay-detail.html", context)


@login_required
def stay_modify(request, pk):
    qs = Stay.objects.prefetch_related("days")
    stay = get_object_or_404(qs, pk=pk)
    trip = stay.days.first().trip
    form = StayForm(
        trip,
        data=request.POST or None,
        instance=stay,
    )
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form, "stay": stay}
    return TemplateResponse(request, "trips/stay-modify.html", context)


@login_required
def stay_delete(request, pk):
    stay = get_object_or_404(Stay, pk=pk)
    trip = stay.days.first().trip
    other_stays = Stay.objects.filter(days__trip=trip).exclude(pk=pk).distinct()

    if request.method == "POST":
        if other_stays.count() == 1:
            # Automatically reassign to the only remaining stay
            new_stay = other_stays.first()
            stay.days.update(stay=new_stay)
        else:
            new_stay_id = request.POST.get("new_stay")
            if new_stay_id:
                new_stay = Stay.objects.get(pk=new_stay_id)
                stay.days.update(stay=new_stay)

        stay.delete()
        messages.add_message(
            request,
            messages.ERROR,
            _("Stay deleted successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    context = {
        "stay": stay,
        "other_stays": other_stays,
        "show_dropdown": other_stays.count() > 1,  # Changed from len() to count()
    }
    return TemplateResponse(request, "trips/stay-delete.html", context)


@login_required
def event_modal(request, pk):
    """
    Modal for showing related event link for unpairing or deleting
    """
    qs = Event.objects.select_related("day__trip__author")
    event = get_object_or_404(qs, pk=pk, day__trip__author=request.user)
    context = {
        "event": event,
    }
    return TemplateResponse(request, "trips/event-modal.html", context)


@login_required
@require_http_methods(["DELETE"])
def event_delete(request, pk):
    qs = Event.objects.select_related("day__trip__author")
    event = get_object_or_404(qs, pk=pk, day__trip__author=request.user)
    event.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
@require_http_methods(["PUT"])
def event_unpair(request, pk):
    """
    Unpair an event from its day by setting the day relation to null.
    Only the trip author can unpair events.
    """
    qs = Event.objects.select_related("trip__author")
    event = get_object_or_404(qs, pk=pk, trip__author=request.user)
    event.day = None
    event.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event unpaired successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
def event_pair(request, pk, day_id):
    """
    Pair an event with a day.
    Only the trip author can pair events.
    """
    qs = Event.objects.select_related("trip__author")
    event = get_object_or_404(qs, pk=pk, trip__author=request.user)
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)

    event.day = day
    event.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event paired successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})


@login_required
def event_pair_choice(request, pk):
    """
    Provide a list of days to pair with the selected event.
    Only days from the same trip are shown.
    """
    event = get_object_or_404(Event, pk=pk, trip__author=request.user)
    trip = event.trip
    days = trip.days.all()

    context = {
        "event": event,
        "days": days,
    }
    return TemplateResponse(request, "trips/event-pair-choice.html", context)


@login_required
def event_detail(request, pk):
    """
    Detail Page for the selected event.
    Uses window functions to efficiently detect event overlaps within the day.
    """
    qs = Event.objects.select_related("trip__author", "transport", "experience", "meal")
    event = get_object_or_404(qs, pk=pk, trip__author=request.user)

    # Get proper instance based on category
    if event.category == 1:  # Transport
        event = event.transport
    elif event.category == 2:  # Experience
        event = event.experience
    elif event.category == 3:  # Meal
        event = event.meal
    else:
        raise Http404("Invalid event category")

    context = {
        "event": event,
        "category": event.category,
    }
    return TemplateResponse(request, "trips/event-detail.html", context)


@login_required
def event_modify(request, pk):
    """
    Modify an event based on its category.
    For Transport/Experience/Meal events, loads the specific instance to access model-specific fields.
    """
    qs = Event.objects.select_related("day__trip", "transport", "experience", "meal")
    event = get_object_or_404(qs, pk=pk, day__trip__author=request.user)

    # Get proper instance based on category
    if event.category == 1:  # Transport
        event = event.transport
    elif event.category == 2:  # Experience
        event = event.experience
    elif event.category == 3:  # Meal
        event = event.meal

    # Select form class based on event category
    event_form = {
        1: TransportForm,  # Transport
        2: ExperienceForm,  # Experience
        3: MealForm,  # Meal
    }.get(event.category)

    if not event_form:
        raise Http404("Invalid event category")

    form = event_form(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Event updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form, "event": event}
    return TemplateResponse(request, "trips/event-modify.html", context)


@login_required
def event_change_times(request, pk):
    """
    Change the times of an event on the event detail card
    """
    qs = Event.objects.select_related("trip__author")
    event = get_object_or_404(qs, pk=pk, trip__author=request.user)
    form = EventChangeTimesForm(request.POST or None, instance=event)
    if form.is_valid():
        event = form.save(commit=False)
        event.start_time = form.cleaned_data["start_time"]
        event.end_time = form.cleaned_data["end_time"]
        event.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Event times updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    return TemplateResponse(
        request, "trips/event-change-times.html", {"event": event, "form": form}
    )


@login_required
def check_event_overlap(request, day_id):
    """
    Check if the proposed event time overlaps with existing events.
    Returns a warning message if there's an overlap.
    """
    start_time = request.GET.get("start_time")
    end_time = request.GET.get("end_time")

    if not (start_time and end_time):
        return HttpResponse("")

    day = get_object_or_404(Day, pk=day_id)

    overlapping_events = Event.objects.filter(
        day=day, start_time__lt=end_time, end_time__gt=start_time
    ).exists()

    if overlapping_events:
        return TemplateResponse(
            request,
            "trips/overlap-warning.html",
            {"message": _("This event overlaps with another event")},
        )

    return HttpResponse("")


@login_required
@require_http_methods(["POST"])
def event_swap(request, pk1, pk2):
    """
    Swap the times of two events.
    Requires both events to belong to the same day and the same trip author.
    """
    event1 = get_object_or_404(Event, pk=pk1, day__trip__author=request.user)
    event2 = get_object_or_404(Event, pk=pk2, day__trip__author=request.user)
    day = event1.day

    try:
        with transaction.atomic():
            event1.swap_times_with(event2)

        messages.success(request, _("Events swapped successfully"))
        return HttpResponse(status=204, headers={"HX-Trigger": f"dayModified{day.pk}"})

    except ValueError as e:
        messages.error(request, str(e))
        return HttpResponse(status=400)


@login_required
def event_swap_modal(request, pk):
    """
    Provide a list of events to swap with the selected event.
    Only events from the same day and trip are shown.
    """
    selected_event = get_object_or_404(Event, pk=pk, day__trip__author=request.user)
    day = selected_event.day
    swappable_events = Event.objects.filter(day=day).exclude(pk=pk)

    context = {
        "selected_event": selected_event,
        "swappable_events": swappable_events,
    }

    return TemplateResponse(request, "trips/event-swap.html", context)


@user_passes_test(lambda u: u.is_staff)
def view_log_file(request, filename):
    """
    View the log file for the application.
    Only accessible to staff users.
    """
    file_path = settings.BASE_DIR / filename
    if file_path.exists():
        with open(file_path) as file:
            response = HttpResponse(file.read(), content_type="text/plain")
            return response
    else:
        raise Http404("Log file does not exist")


def validate_dates(request):
    """
    Validate the start and end dates of a trip.
    If the start date is after the end date or before today, return an HTML snippet with an error message.
    """
    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    errors = []

    # Parse dates if present
    try:
        if start_date:
            start_date_obj = date.fromisoformat(start_date)
        else:
            start_date_obj = None
        if end_date:
            end_date_obj = date.fromisoformat(end_date)
        else:
            end_date_obj = None
    except ValueError:
        # If parsing fails, skip further checks
        return HttpResponse("")

    # Check if start_date is before today
    if start_date_obj and start_date_obj < date.today():
        errors.append(_("Start date must be after today."))

    # Check if start_date is after end_date
    if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
        errors.append(_("Start date cannot be after end date."))

    if errors:
        html = "".join(
            [
                format_html(
                    """
                <div class="alert alert-error alert-soft flex items-center gap-2 mt-2" x-data>
                    <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M12 8v4m0 4h.01M21 12A9 9 0 1 1 3 12a9 9 0 0 1 18 0Z" />
                    </svg>
                    <span>{}</span>
                </div>
                """,
                    error,
                )
                for error in errors
            ]
        )
        return HttpResponse(html)
    return HttpResponse("")


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


@login_required
def event_notes(request, event_id):
    """
    View or edit the notes for an event (now a field on Event).
    """
    event = get_object_or_404(Event, pk=event_id, trip__author=request.user)
    form = NoteForm(instance=event)
    context = {
        "event": event,
        "form": form,
    }
    return TemplateResponse(request, "trips/event-notes.html", context)


@login_required
@require_http_methods(["POST"])
def note_create(request, event_id):
    """
    Add or update a note for an event (now a field on Event).
    """
    event = get_object_or_404(Event, pk=event_id, trip__author=request.user)
    form = NoteForm(request.POST, instance=event)
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Note added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    return HttpResponse(status=400)


@login_required
def note_modify(request, event_id):
    """
    Modify the note for an event (now a field on Event).
    """
    event = get_object_or_404(Event, pk=event_id, trip__author=request.user)
    form = NoteForm(request.POST or None, instance=event)
    context = {"form": form, "event": event}
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Note updated successfully"),
        )
        response = TemplateResponse(request, "trips/event-notes.html", context)
        response["HX-Trigger"] = "tripModified"
        return response
    return TemplateResponse(request, "trips/note-modify.html", context)


@login_required
def note_delete(request, event_id):
    """
    Delete the note from an event (clear the notes field).
    """
    event = get_object_or_404(Event, pk=event_id, trip__author=request.user)
    event.notes = ""
    event.save()
    messages.add_message(
        request,
        messages.ERROR,
        _("Note deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})


@login_required
def stay_notes(request, stay_id):
    """
    View the note for an event.
    """
    stay = get_object_or_404(Stay, pk=stay_id)
    form = AddNoteToStayForm(instance=stay)
    context = {
        "stay": stay,
        "form": form,
    }
    return TemplateResponse(request, "trips/stay-notes.html", context)


@login_required
@require_http_methods(["POST"])
def stay_note_create(request, stay_id):
    """
    Add a note to a stay. If the stay already has a note, do not create a new one.
    """
    stay = get_object_or_404(Stay, pk=stay_id)
    form = AddNoteToStayForm(request.POST)
    if form.is_valid():
        notes_content = form.cleaned_data["notes"]
        stay.notes = notes_content
        stay.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Note added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    return HttpResponse(status=400)


@login_required
def stay_note_modify(request, stay_id):
    """
    Modify a note for a stay. If the note does not exist, return 404.
    """
    stay = get_object_or_404(Stay, pk=stay_id)
    form = AddNoteToStayForm(request.POST or None, instance=stay)
    context = {
        "form": form,
        "stay": stay,
    }
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Note updated successfully"),
        )
        response = TemplateResponse(request, "trips/stay-notes.html", context)
        response["HX-Trigger"] = "tripModified"
        return response
    return TemplateResponse(request, "trips/stay-note-modify.html", context)


@login_required
def stay_note_delete(request, stay_id):
    """
    Delete a note from a stay. If the note does not exist, return 404.
    """
    stay = get_object_or_404(Stay, pk=stay_id)
    stay.notes = ""
    stay.save()
    messages.add_message(
        request,
        messages.ERROR,
        _("Note deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})


# @login_required
# def event_detail(request, pk):
#     """
#     Get single event details in case of modification instead of refreshing the whole trip detail page
#     """
#     pass

# @login_required
# def stay_detail(request, day_id):
#     """
#     Get single stay for the day details in case of modification instead of refreshing the whole trip detail page
#     """
#     # TODO: think about refreshing the same stay in other days
#     pass
