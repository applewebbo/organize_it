import json
import logging
import math
from datetime import date, timedelta

import geocoder
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required, user_passes_test
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.db.models import Max, Min, Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override as translation_override
from django.views.decorators.http import require_http_methods

from accounts.models import Profile, get_profile
from trips.forms import (
    AddNoteToStayForm,
    CarMainTransferForm,
    ExperienceForm,
    FlightMainTransferForm,
    MealForm,
    NoteForm,
    OtherMainTransferForm,
    ShareLinkCreateForm,
    StayForm,
    StayTransferCreateForm,
    StayTransferEditForm,
    TrainMainTransferForm,
    TripForm,
)
from trips.models import (
    Day,
    Event,
    MainTransfer,
    ShareLink,
    Stay,
    StayTransfer,
    Trip,
    TripCollaboration,
    TripInvitation,
)
from trips.services import GooglePlacesClient, GooglePlacesError
from trips.utils import (
    accessible_trips_qs,
    create_day_map,
    create_trip_map,
    download_unsplash_photo,
    editable_trips_qs,
    geocode_location,
    get_airport_by_iata,
    get_event_instance,
    get_flight_origin_icao,
    get_trip_for_editor_or_404,
    get_trip_for_owner_or_404,
    get_trip_or_404,
    get_trip_stages,
    get_trips,
    group_days_by_destination,
    process_trip_image,
    search_airports,
    search_train_stations,
    search_unsplash_photos,
)

logger = logging.getLogger(__name__)


@login_not_required
def home(request):
    """Home page"""
    context = {}
    if request.user.is_authenticated:
        try:
            context = get_trips(request.user)
            context["show_guide"] = request.session.get("show_guide", False)
        except Profile.DoesNotExist:
            pass
    return TemplateResponse(request, "trips/index.html", context)


def toggle_guide(request):
    """Toggle the visibility of the quick guide in home page"""
    if request.method == "POST":
        current_state = request.session.get("show_guide", False)
        request.session["show_guide"] = not current_state
    return HttpResponse(status=204)


def trip_list(request):
    """List of all trips"""
    if request.htmx:
        template = "trips/trip-list.html#trip-list"
    else:
        template = "trips/trip-list.html"

    # Get user's sort preference
    sort_preference = get_profile(request.user).trip_sort_preference

    # Build base querysets
    active_trips = Trip.objects.filter(author=request.user).exclude(status=5)
    archived_trips = Trip.objects.filter(author=request.user, status=5)
    shared_trips = Trip.objects.filter(collaborators=request.user).exclude(status=5)

    # Apply sorting based on preference
    sort_map = {
        "date_asc": "start_date",
        "date_desc": "-start_date",
        "name_asc": "title",
        "name_desc": "-title",
    }

    order_by = sort_map.get(sort_preference, "start_date")
    active_trips = active_trips.order_by(order_by)
    archived_trips = archived_trips.order_by(order_by)
    shared_trips = shared_trips.order_by(order_by)

    context = {
        "active_trips": active_trips,
        "archived_trips": archived_trips,
        "shared_trips": shared_trips,
    }
    return TemplateResponse(request, template, context)


def trip_detail(request, pk):
    """
    Detail Page for the selected trip.
    Uses window functions to efficiently detect event overlaps within each day.
    """

    qs = Trip.objects.prefetch_related(
        Prefetch(
            "days__events",
            queryset=Event.objects.all().order_by("order", "pk"),
        ),
        Prefetch(
            "days__stay",
            queryset=Stay.objects.select_related("author").prefetch_related(
                "transfer_from", "transfer_to"
            ),
        ),
        Prefetch(
            "collaborations",
            queryset=TripCollaboration.objects.select_related("user__profile"),
        ),
    ).select_related("author")

    trip = get_object_or_404(
        qs.filter(Q(author=request.user) | Q(collaborators=request.user)).distinct(),
        pk=pk,
    )
    unpaired_events = trip.all_events.filter(day__isnull=True)

    # Get unique stays ordered by first day date
    stays = (
        Stay.objects.filter(days__trip=trip)
        .annotate(first_day_date=Min("days__date"), last_day_date=Max("days__date"))
        .distinct()
        .order_by("first_day_date")
    )

    # Get main transfers
    arrival_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.DEPARTURE
    ).first()

    # Check user preference for default view
    default_view = get_profile(request.user).default_map_view
    show_map = default_view == "map"

    days = trip.days.all()
    day_groups = group_days_by_destination(days)

    context = {
        "trip": trip,
        "stays": stays,
        "unpaired_events": unpaired_events,
        "arrival_transfer": arrival_transfer,
        "departure_transfer": departure_transfer,
        "both_transfers_exist": arrival_transfer is not None
        and departure_transfer is not None,
        "show_map": show_map,
        "today": date.today(),
        "arrival_origin_icao": get_flight_origin_icao(arrival_transfer),
        "departure_origin_icao": get_flight_origin_icao(departure_transfer),
        "day_groups": day_groups,
    }
    if request.htmx:
        template = "trips/trip-detail.html#days"
    else:
        template = "trips/trip-detail.html"
    return TemplateResponse(request, template, context)


def day_detail(request, pk):
    """
    Detail Page for the selected day.
    Uses window functions to efficiently detect event overlaps within the day.
    """
    qs = Day.objects.prefetch_related(
        Prefetch(
            "events",
            queryset=Event.objects.order_by("order", "pk"),
        ),
        Prefetch(
            "stay",
            queryset=Stay.objects.select_related("author"),
        ),
        "trip__main_transfers",
        Prefetch(
            "trip__collaborations",
            queryset=TripCollaboration.objects.all(),
        ),
    ).select_related("trip__author")

    day = get_object_or_404(qs, pk=pk, trip__in=accessible_trips_qs(request.user))

    # Check for forced view from query parameter, otherwise use user preference
    force_view = request.GET.get("view")
    if force_view in ["list", "map"]:
        show_map = force_view == "map"
    else:
        default_view = get_profile(request.user).default_map_view
        show_map = default_view == "map"

    # Check if there's a StayTransfer from this day to the next
    # Use explicit DB query to avoid Django's reverse relation caching issues
    # Only show transfer_out on the last day of the stay (when next day has different stay)
    next_day = day.next_day
    is_last_day_of_stay = not next_day or not next_day.stay or next_day.stay != day.stay
    stay_transfer_out = (
        StayTransfer.objects.filter(from_stay=day.stay).first()
        if day.stay and is_last_day_of_stay
        else None
    )

    # Check if there's a StayTransfer to this day from the previous
    stay_transfer_in = (
        StayTransfer.objects.filter(to_stay=day.stay).first() if day.stay else None
    )

    # Check if can add StayTransfer (next day exists, both have stays, different stays)
    can_add_stay_transfer = False
    if (
        next_day
        and day.stay
        and hasattr(next_day, "stay")
        and next_day.stay
        and day.stay != next_day.stay
        and not stay_transfer_out
    ):
        can_add_stay_transfer = True

    context = {
        "day": day,
        "show_map": show_map,
        "stay_transfer_out": stay_transfer_out,
        "stay_transfer_in": stay_transfer_in,
        "can_add_stay_transfer": can_add_stay_transfer,
        "next_day": next_day,
    }

    # If map view is preferred, prepare map context
    if show_map:
        events = day.events.exclude(category=1)
        stay = day.stay
        next_day = day.next_day
        prev_day = day.prev_day
        next_day_stay = None
        if next_day and next_day.stay and next_day.stay != stay:
            next_day_stay = next_day.stay
        is_last_day = not next_day
        is_first_day = not prev_day

        # Get MainTransfers for first and last day
        arrival_transfer = None
        departure_transfer = None
        if is_first_day:
            arrival_transfer = day.trip.main_transfers.filter(direction=1).first()
        if is_last_day:
            departure_transfer = day.trip.main_transfers.filter(direction=2).first()

        locations = {
            "stay": stay,
            "events": events,
            "next_day_stay": next_day_stay,
            "last_day": is_last_day,
            "arrival_transfer": arrival_transfer,
            "departure_transfer": departure_transfer,
            "can_add_stay_transfer": can_add_stay_transfer,
            "stay_transfer_out": stay_transfer_out,
            "day": day,
        }
        if not (prev_day and prev_day.stay and prev_day.stay == stay):
            locations["first_day"] = True

        # Filter out events without latitude or longitude
        events_with_location = events.filter(
            latitude__isnull=False, longitude__isnull=False
        )

        map_obj = create_day_map(events_with_location, stay, next_day_stay, day=day)
        context["map"] = map_obj
        context["locations"] = locations

    # Use wrapper template for HTMX requests to include OOB message swap
    template = (
        "trips/day-detail-wrapper.html" if request.htmx else "trips/includes/day.html"
    )
    return TemplateResponse(request, template, context)


def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST, request.FILES)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.author = request.user

            # Handle Unsplash photo selection
            selected_photo_id = form.cleaned_data.get("selected_photo_id")
            if selected_photo_id:
                # Search Unsplash to get photo data
                query = trip.destination
                photos = search_unsplash_photos(query, per_page=10)
                if photos:
                    photo_data = next(
                        (p for p in photos if p["id"] == selected_photo_id), None
                    )
                    if photo_data:
                        # Download and process image
                        image_content, metadata = download_unsplash_photo(photo_data)
                        if image_content:
                            processed_image = process_trip_image(image_content)
                            if processed_image:
                                filename = f"trip_{selected_photo_id}.jpg"
                                trip.image.save(filename, processed_image, save=False)
                                trip.image_metadata = metadata

            # Process uploaded image if present (overrides Unsplash)
            if request.FILES.get("image"):  # pragma: no cover
                processed_image = process_trip_image(request.FILES["image"])
                if processed_image:
                    trip.image = processed_image
                    trip.image_metadata = {"source": "upload"}

            trip.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                _("<strong>%(title)s</strong> added successfully")
                % {"title": trip.title},
            )
            if request.GET.get("next") == "list":
                return HttpResponse(
                    status=204, headers={"HX-Redirect": reverse("trips:trip-list")}
                )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm()
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-create.html", context)


@require_http_methods(["DELETE"])
def trip_delete(request, pk):
    trip = get_trip_for_owner_or_404(pk, request.user)
    trip.delete()
    messages.add_message(
        request,
        messages.ERROR,
        _("<strong>%(title)s</strong> deleted successfully") % {"title": trip.title},
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


def trip_update(request, pk):
    trip = get_trip_for_editor_or_404(pk, request.user)
    if request.method == "POST":
        form = TripForm(request.POST, request.FILES, instance=trip)
        if form.is_valid():
            trip = form.save(commit=False)

            # Handle Unsplash photo selection
            selected_photo_id = form.cleaned_data.get("selected_photo_id")
            if selected_photo_id:
                # Search Unsplash to get photo data
                query = trip.destination
                photos = search_unsplash_photos(query, per_page=10)
                if photos:
                    photo_data = next(
                        (p for p in photos if p["id"] == selected_photo_id), None
                    )
                    if photo_data:
                        # Download and process image
                        image_content, metadata = download_unsplash_photo(photo_data)
                        if image_content:
                            processed_image = process_trip_image(image_content)
                            if processed_image:
                                filename = f"trip_{trip.pk}_{selected_photo_id}.jpg"
                                trip.image.save(filename, processed_image, save=False)
                                trip.image_metadata = metadata

            # Process uploaded image if present (overrides Unsplash)
            if request.FILES.get("image"):  # pragma: no cover
                processed_image = process_trip_image(request.FILES["image"])
                if processed_image:
                    trip.image = processed_image
                    trip.image_metadata = {"source": "upload"}

            trip.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                _("<strong>%(title)s</strong> updated successfully")
                % {"title": trip.title},
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        context = {"form": form, "is_update": True}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm(instance=trip)
    context = {"form": form, "is_update": True}
    return TemplateResponse(request, "trips/trip-create.html", context)


def trip_archive(request, pk):
    trip = get_trip_for_owner_or_404(pk, request.user)
    trip.status = 5
    trip.save()

    # Reset fav_trip if this trip was the favourite
    profile = get_profile(request.user)
    if profile.fav_trip == trip:
        profile.fav_trip = None
        profile.save()

    messages.add_message(
        request,
        messages.SUCCESS,
        _("<strong>%(title)s</strong> archived successfully") % {"title": trip.title},
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


def trip_unarchive(request, pk):
    trip = get_trip_for_owner_or_404(pk, request.user)
    trip.status = Trip.Status.NOT_STARTED
    trip.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("<strong>%(title)s</strong> unarchived successfully") % {"title": trip.title},
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved", "HX-Refresh": "true"},
    )


@require_http_methods(["POST"])
def reorder_events(request, day_id):
    """Save new event order after drag & drop. Expects JSON body: {"order": [pk1, pk2, ...]}"""
    import json

    day = get_object_or_404(Day, pk=day_id, trip__in=editable_trips_qs(request.user))
    try:
        data = json.loads(request.body)
        ordered_pks = data.get("order", [])
    except json.JSONDecodeError, AttributeError:
        return HttpResponse(status=400)

    events = Event.objects.filter(day=day, pk__in=ordered_pks)
    pk_to_event = {e.pk: e for e in events}

    with transaction.atomic():
        for i, pk in enumerate(ordered_pks):
            event = pk_to_event.get(int(pk))
            if event:
                event.order = i
                event.save(update_fields=["order"])

    return HttpResponse(status=204)


@require_http_methods(["GET"])
def swap_event_order_modal(request, event_id):
    event = get_object_or_404(
        Event,
        pk=event_id,
        day__trip__in=accessible_trips_qs(request.user),
    )
    other_events = (
        Event.objects.filter(day=event.day).exclude(pk=event_id).order_by("order", "pk")
    )
    return TemplateResponse(
        request,
        "trips/swap-event-order-modal.html",
        {"event": event, "other_events": other_events},
    )


@require_http_methods(["POST"])
def swap_event_order(request, event_id):
    """Swap order between two events on the same day (mobile reorder)."""
    event = get_object_or_404(
        Event,
        pk=event_id,
        day__trip__in=editable_trips_qs(request.user),
    )
    try:
        other_id = int(request.POST.get("other_event_id", ""))
    except ValueError, TypeError:
        return HttpResponse(status=400)

    other = get_object_or_404(Event, pk=other_id, day=event.day)

    with transaction.atomic():
        event.order, other.order = other.order, event.order
        event.save(update_fields=["order"])
        other.save(update_fields=["order"])

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": f"dayModified{event.day.pk}"},
    )


def add_experience(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__in=editable_trips_qs(request.user))
    unpaired_experiences = Event.objects.filter(
        day__isnull=True, trip=day.trip, category=2
    )
    form = ExperienceForm(
        request.POST or None, initial={"city": day.trip.destination}, geocode=True
    )
    if form.is_valid():
        experience = form.save(commit=False)
        experience.day = day
        experience.last_modified_by = request.user
        max_order = (
            Event.objects.filter(day=day).aggregate(m=models.Max("order"))["m"] or 0
        )
        experience.order = max_order + 1
        experience.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Experience added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": f"dayModified{day.pk}"})
    context = {"form": form, "day": day, "unpaired_experiences": unpaired_experiences}
    return TemplateResponse(request, "trips/experience-create.html", context)


def add_meal(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__in=editable_trips_qs(request.user))
    unpaired_experiences = Event.objects.filter(
        day__isnull=True, trip=day.trip, category=3
    )
    form = MealForm(
        request.POST or None, initial={"city": day.trip.destination}, geocode=True
    )
    if form.is_valid():
        meal = form.save(commit=False)
        meal.day = day
        meal.last_modified_by = request.user
        max_order = (
            Event.objects.filter(day=day).aggregate(m=models.Max("order"))["m"] or 0
        )
        meal.order = max_order + 1
        meal.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Meal added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": f"dayModified{day.pk}"})
    context = {"form": form, "day": day, "unpaired_experiences": unpaired_experiences}
    return TemplateResponse(request, "trips/meal-create.html", context)


def add_experience_to_trip(request, trip_pk):
    trip = get_trip_for_editor_or_404(trip_pk, request.user)
    form = ExperienceForm(
        request.POST or None, initial={"city": trip.destination}, geocode=True
    )
    if form.is_valid():
        experience = form.save(commit=False)
        experience.trip = trip
        experience.last_modified_by = request.user
        experience.save()
        messages.add_message(
            request, messages.SUCCESS, _("Experience added successfully")
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "unpairedModified"})
    context = {"form": form, "trip": trip}
    return TemplateResponse(request, "trips/experience-create-unpaired.html", context)


def add_meal_to_trip(request, trip_pk):
    trip = get_trip_for_editor_or_404(trip_pk, request.user)
    form = MealForm(
        request.POST or None, initial={"city": trip.destination}, geocode=True
    )
    if form.is_valid():
        meal = form.save(commit=False)
        meal.trip = trip
        meal.last_modified_by = request.user
        meal.save()
        messages.add_message(request, messages.SUCCESS, _("Meal added successfully"))
        return HttpResponse(status=204, headers={"HX-Trigger": "unpairedModified"})
    context = {"form": form, "trip": trip}
    return TemplateResponse(request, "trips/meal-create-unpaired.html", context)


def add_stay_for_trip(request, trip_pk):
    trip = get_trip_for_editor_or_404(trip_pk, request.user)
    form = StayForm(
        trip,
        data=request.POST or None,
        initial={"city": trip.destination},
        geocode=True,
    )
    if form.is_valid():
        stay = form.save()
        Stay.objects.filter(pk=stay.pk).update(author=request.user)
        messages.add_message(request, messages.SUCCESS, _("Stay added successfully"))
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form}
    return TemplateResponse(request, "trips/stay-create.html", context)


def add_stay(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__in=editable_trips_qs(request.user))
    trip = day.trip
    form = StayForm(
        trip,
        data=request.POST or None,
        initial={"apply_to_days": [day_id], "city": trip.destination},
        geocode=True,
    )
    if form.is_valid():
        stay = form.save()
        Stay.objects.filter(pk=stay.pk).update(author=request.user)
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form}
    return TemplateResponse(request, "trips/stay-create.html", context)


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
            "modified": True,
        }
        return TemplateResponse(request, "trips/stay-detail.html", context)
    context = {"form": form, "stay": stay}
    return TemplateResponse(request, "trips/stay-modify.html", context)


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


# ============================================================================
# StayTransfer Views
# ============================================================================


def create_stay_transfer(request, from_day_id):
    """
    Create a StayTransfer between stays of consecutive days.
    The from_stay and to_stay are auto-populated from the days.
    The button to create a transfer only appears on the last day of a stay
    (where next_day has a different stay), so next_day is the correct to_day.
    """
    from_day = get_object_or_404(
        Day, pk=from_day_id, trip__in=editable_trips_qs(request.user)
    )

    # Get the next day - the button only appears when next_day exists and has different stay
    to_day = from_day.next_day
    if not to_day:
        messages.add_message(
            request,
            messages.ERROR,
            _("No next day found for this stay"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    # Check if both days have stays
    if not from_day.stay or not to_day.stay:
        messages.add_message(
            request,
            messages.ERROR,
            _("Both days must have stays to create a transfer"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    from_stay = from_day.stay
    to_stay = to_day.stay

    # Check if stays are different (can't transfer from/to same stay)
    if from_stay == to_stay:
        messages.add_message(
            request,
            messages.ERROR,
            _("Cannot create transfer between the same stay"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    form = StayTransferCreateForm(
        request.POST or None,
        from_stay=from_stay,
        to_stay=to_stay,
    )

    if form.is_valid():
        stay_transfer = form.save(commit=False)
        # from_stay and to_event are already set by the form's __init__
        stay_transfer.from_day = from_day
        stay_transfer.to_day = to_day
        stay_transfer.trip = from_day.trip
        stay_transfer.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay transfer created successfully"),
        )
        # Trigger both days to refresh
        triggers = {f"dayModified{from_day.pk}": {}, f"dayModified{to_day.pk}": {}}
        return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(triggers)})

    context = {
        "form": form,
        "from_day": from_day,
        "to_day": to_day,
        "from_stay": from_stay,
        "to_stay": to_stay,
    }
    return TemplateResponse(request, "trips/stay-transfer-create.html", context)


def edit_stay_transfer(request, pk):
    """Edit an existing StayTransfer"""
    qs = StayTransfer.objects.select_related(
        "from_stay", "to_stay", "from_day__trip__author", "to_day", "trip"
    )
    stay_transfer = get_object_or_404(
        qs, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    form = StayTransferEditForm(request.POST or None, instance=stay_transfer)

    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay transfer updated successfully"),
        )
        # Trigger both days to refresh
        triggers = {
            f"dayModified{stay_transfer.from_day.pk}": {},
            f"dayModified{stay_transfer.to_day.pk}": {},
        }
        return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(triggers)})

    context = {"form": form, "stay_transfer": stay_transfer}
    return TemplateResponse(request, "trips/stay-transfer-edit.html", context)


def delete_stay_transfer(request, pk):
    """Delete a StayTransfer"""
    qs = StayTransfer.objects.select_related("from_day__trip__author", "to_day")
    stay_transfer = get_object_or_404(
        qs, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    from_day_id = stay_transfer.from_day.pk
    to_day_id = stay_transfer.to_day.pk
    stay_transfer.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Stay transfer deleted successfully"),
    )
    # Trigger refresh of both days to update their UI
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": f"dayModified{from_day_id}, dayModified{to_day_id}"},
    )


def edit_main_transfer(request, pk):
    """Edit existing main transfer - opens modal with specific form"""
    transfer = get_object_or_404(
        MainTransfer, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    trip = transfer.trip

    # Form class mapper
    FORM_MAP = {
        MainTransfer.Type.PLANE: FlightMainTransferForm,
        MainTransfer.Type.TRAIN: TrainMainTransferForm,
        MainTransfer.Type.CAR: CarMainTransferForm,
        MainTransfer.Type.OTHER: OtherMainTransferForm,
    }

    form_class = FORM_MAP[transfer.type]

    if request.method == "POST":
        # Handle form submission
        form = form_class(
            request.POST,
            instance=transfer,
            trip=trip,
            autocomplete=True,
            home_address="",
        )
        if form.is_valid():
            form.save()
            message = str(_("Main transfer updated successfully"))
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps(
                        {
                            "tripModified": {},
                            "hide-modal": {},
                            "showMessage": {
                                "type": "success",
                                "message": message,
                            },
                        }
                    )
                },
            )
        # If form is invalid, fall through to return form with errors
    else:
        # GET request - show form with existing data
        form = form_class(
            instance=transfer, trip=trip, autocomplete=True, home_address=""
        )

    direction_str = (
        "arrival"
        if transfer.direction == MainTransfer.Direction.ARRIVAL
        else "departure"
    )

    context = {
        "trip": trip,
        "form": form,
        "transport_type": transfer.type,
        "direction": direction_str,
        "is_edit": True,
        "is_edit_modal": True,
    }

    return TemplateResponse(request, "trips/edit-main-transfer-modal.html", context)


def delete_main_transfer(request, pk):
    """Delete main transfer"""
    transfer = get_object_or_404(
        MainTransfer, pk=pk, trip__in=editable_trips_qs(request.user)
    )

    transfer.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Main transfer deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


def train_status_redirect(request, pk):
    """Redirect to viaggiatreno for train status (specific train or station board)."""
    transfer = get_object_or_404(
        MainTransfer,
        pk=pk,
        trip__in=accessible_trips_qs(request.user),
        type=MainTransfer.Type.TRAIN,
    )

    base = (
        "http://www.viaggiatreno.it/infomobilitamobile/pages/cercaTreno/cercaTreno.jsp"
    )
    train_number = transfer.train_number

    if train_number:
        # Specific train: look up origin station id and datapartenza
        try:
            resp = requests.get(
                f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
                f"/cercaNumeroTrenoTrenoAutocomplete/{train_number}",
                timeout=5,
            )
            if resp.ok and resp.text:
                # Format: "2822 - MILANO CENTRALE - 23/03/26|2822-S01700-1774220400000"
                token = resp.text.strip().split("|")[-1]  # "2822-S01700-1774220400000"
                parts = token.split("-")
                if len(parts) == 3:
                    _, origine, datapartenza = parts
                    return redirect(
                        f"{base}?treno={train_number}&origine={origine}&datapartenza={datapartenza}"
                    )
        except Exception as exc:
            logger.warning(
                "Viaggiatreno train lookup failed for %s: %s", train_number, exc
            )

    # Fallback: station departure board
    station_name = transfer.origin_name
    first_word = station_name.split()[0] if station_name else ""
    try:
        resp = requests.get(
            f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
            f"/cercaStazione/{first_word}",
            timeout=5,
        )
        if resp.ok:
            stations = resp.json()
            # Find best match by normalized name
            match = next(
                (s for s in stations if s["nomeLungo"].upper() == station_name.upper()),
                stations[0] if stations else None,
            )
            if match:
                from urllib.parse import quote as urlquote

                nome = urlquote(match["nomeLungo"])
                return redirect(f"{base}?cod={match['id']}&nome={nome}")
    except Exception as exc:
        logger.warning(
            "Viaggiatreno station lookup failed for %s: %s", station_name, exc
        )

    # Last resort: viaggiatreno homepage
    return redirect("http://www.viaggiatreno.it/infomobilitamobile/pages/home/home.jsp")


def flight_status_redirect(request, pk):
    """Redirect to FlightAware for flight status (specific flight or airport board)."""
    transfer = get_object_or_404(
        MainTransfer,
        pk=pk,
        trip__in=accessible_trips_qs(request.user),
        type=MainTransfer.Type.PLANE,
    )

    flight_number = transfer.flight_number
    if flight_number:
        return redirect(f"https://it.flightaware.com/live/flight/{flight_number}")

    # Fallback: airport departure/arrival board via ICAO code
    iata_code = transfer.origin_code
    if iata_code:
        airport = get_airport_by_iata(iata_code)
        if airport and airport.get("icao_code"):
            return redirect(
                f"https://it.flightaware.com/live/airport/{airport['icao_code']}"
            )

    return redirect("https://it.flightaware.com")


def main_transfers_section(request, trip_id):
    """HTMX endpoint: returns main transfers section for trip detail page"""
    trip = get_trip_or_404(trip_id, request.user)

    # Get main transfers
    arrival_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.DEPARTURE
    ).first()

    context = {
        "trip": trip,
        "arrival_transfer": arrival_transfer,
        "departure_transfer": departure_transfer,
        "both_transfers_exist": arrival_transfer is not None
        and departure_transfer is not None,
        "today": date.today(),
        "arrival_origin_icao": get_flight_origin_icao(arrival_transfer),
        "departure_origin_icao": get_flight_origin_icao(departure_transfer),
    }

    return TemplateResponse(request, "trips/includes/main-transfers.html", context)


def event_modal(request, pk):
    """
    Modal for showing related event link for unpairing or deleting
    """
    qs = Event.objects.select_related("day__trip__author")
    event = get_object_or_404(qs, pk=pk, trip__in=accessible_trips_qs(request.user))
    context = {
        "event": event,
    }
    return TemplateResponse(request, "trips/event-modal.html", context)


@require_http_methods(["DELETE"])
def event_delete(request, pk):
    qs = Event.objects.select_related("day__trip__author")
    event = get_object_or_404(qs, pk=pk, trip__in=editable_trips_qs(request.user))
    event.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@require_http_methods(["PUT"])
def event_unpair(request, pk):
    """
    Unpair an event from its day by setting the day relation to null.
    Only the trip author can unpair events.
    """
    qs = Event.objects.select_related("trip__author")
    event = get_object_or_404(qs, pk=pk, trip__in=editable_trips_qs(request.user))
    event.day = None
    event.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event unpaired successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


def event_pair(request, pk, day_id):
    """
    Pair an event with a day.
    Only the trip author can pair events.
    """
    qs = Event.objects.select_related("trip__author")
    event = get_object_or_404(qs, pk=pk, trip__in=editable_trips_qs(request.user))
    day = get_object_or_404(Day, pk=day_id, trip__in=editable_trips_qs(request.user))

    event.day = day
    event.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event paired successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": "unpairedModified"})


def event_pair_choice(request, pk):
    """
    Provide a list of days to pair with the selected event.
    Only days from the same trip are shown.
    """
    event = get_object_or_404(Event, pk=pk, trip__in=accessible_trips_qs(request.user))
    trip = event.trip
    days = trip.days.all()

    context = {
        "event": event,
        "days": days,
    }
    return TemplateResponse(request, "trips/event-pair-choice.html", context)


# ============================================================================
# MainTransferConnection Views
# ============================================================================


def main_transfer_connection_modal(request, main_transfer_pk):
    """Show modal with event/stay options for creating a main transfer connection"""
    from trips.models import MainTransfer, MainTransferConnection

    main_transfer = get_object_or_404(
        MainTransfer, pk=main_transfer_pk, trip__in=accessible_trips_qs(request.user)
    )

    # Check if connection already exists
    existing_connection = None
    try:
        existing_connection = main_transfer.connection
    except MainTransferConnection.DoesNotExist:
        pass

    trip = main_transfer.trip

    # Determine available options based on direction
    if main_transfer.direction == MainTransfer.Direction.ARRIVAL:
        # For ARRIVAL: first day's stay and first event
        first_day = trip.days.first()
        available_stay = first_day.stay if first_day else None
        available_event = (
            first_day.events.order_by("order", "pk").first() if first_day else None
        )
    else:
        # For DEPARTURE: last day's stay and last event
        last_day = trip.days.last()
        available_stay = last_day.stay if last_day else None
        available_event = (
            last_day.events.order_by("order", "pk").last() if last_day else None
        )

    context = {
        "main_transfer": main_transfer,
        "existing_connection": existing_connection,
        "available_stay": available_stay,
        "available_event": available_event,
    }
    return TemplateResponse(
        request, "trips/main-transfer-connection-modal.html", context
    )


def create_main_transfer_connection(request, main_transfer_pk, destination_type):
    """Create a MainTransferConnection to event or stay"""
    from trips.models import MainTransfer

    main_transfer = get_object_or_404(
        MainTransfer, pk=main_transfer_pk, trip__in=editable_trips_qs(request.user)
    )

    # Check if connection already exists
    if hasattr(main_transfer, "connection"):
        messages.add_message(
            request,
            messages.ERROR,
            _("A connection already exists for this main transfer"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    trip = main_transfer.trip

    # Get the destination based on type and direction
    if destination_type not in ["event", "stay"]:
        messages.add_message(
            request,
            messages.ERROR,
            _("Invalid destination type"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    # Determine the destination object
    if main_transfer.direction == MainTransfer.Direction.ARRIVAL:
        first_day = trip.days.first()
        if not first_day:
            messages.add_message(
                request,
                messages.ERROR,
                _("No days available in this trip"),
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})

        if destination_type == "stay":
            destination = first_day.stay
        else:
            destination = first_day.events.order_by("order", "pk").first()
    else:
        # DEPARTURE
        last_day = trip.days.last()
        if not last_day:
            messages.add_message(
                request,
                messages.ERROR,
                _("No days available in this trip"),
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})

        if destination_type == "stay":
            destination = last_day.stay
        else:
            destination = last_day.events.order_by("order", "pk").last()

    if not destination:
        messages.add_message(
            request,
            messages.ERROR,
            _(f"No {destination_type} available for this connection"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    # Create form
    from trips.forms import MainTransferConnectionForm

    form = MainTransferConnectionForm(
        request.POST or None,
        main_transfer=main_transfer,
        destination=destination,
        destination_type=destination_type,
    )

    if form.is_valid():
        connection = form.save(commit=False)
        connection.main_transfer = main_transfer
        if destination_type == "event":
            connection.event = destination
        else:
            connection.stay = destination
        connection.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Connection created successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    context = {
        "form": form,
        "main_transfer": main_transfer,
        "destination": destination,
        "destination_type": destination_type,
    }
    return TemplateResponse(
        request, "trips/main-transfer-connection-create.html", context
    )


def edit_main_transfer_connection(request, pk):
    """Edit an existing MainTransferConnection"""
    from trips.models import MainTransferConnection

    qs = MainTransferConnection.objects.select_related(
        "main_transfer__trip__author", "event", "stay"
    )
    connection = get_object_or_404(
        qs, pk=pk, main_transfer__trip__in=editable_trips_qs(request.user)
    )

    from trips.forms import MainTransferConnectionEditForm

    form = MainTransferConnectionEditForm(request.POST or None, instance=connection)

    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Connection updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    context = {"form": form, "connection": connection}
    return TemplateResponse(
        request, "trips/main-transfer-connection-edit.html", context
    )


def delete_main_transfer_connection(request, pk):
    """Delete a MainTransferConnection"""
    from trips.models import MainTransferConnection

    qs = MainTransferConnection.objects.select_related("main_transfer__trip__author")
    connection = get_object_or_404(
        qs, pk=pk, main_transfer__trip__in=editable_trips_qs(request.user)
    )
    connection.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Connection deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})


def event_detail(request, pk):
    """
    Detail Page for the selected event.
    Uses window functions to efficiently detect event overlaps within the day.
    """
    qs = Event.objects.select_related("trip__author", "experience", "meal")
    event = get_object_or_404(qs, pk=pk, trip__in=accessible_trips_qs(request.user))

    event = get_event_instance(event)

    context = {
        "event": event,
    }
    return TemplateResponse(request, "trips/event-detail.html", context)


def event_modify(request, pk):
    """
    Modify an event based on its category.
    For Experience/Meal events, loads the specific instance to access model-specific fields.
    """
    qs = Event.objects.select_related("day__trip", "experience", "meal")
    event = get_object_or_404(qs, pk=pk, trip__in=editable_trips_qs(request.user))

    event = get_event_instance(event)

    # Select form class based on event category
    event_form = {
        2: ExperienceForm,  # Experience
        3: MealForm,  # Meal
    }.get(event.category)

    form = event_form(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        context = {
            "event": event,
            "category": event.category,
        }
        response = TemplateResponse(request, "trips/event-detail.html", context)
        response["HX-Trigger"] = f"eventModified{event.pk}"
        return response
    context = {"form": form, "event": event}
    return TemplateResponse(request, "trips/event-modify.html", context)


def single_event(request, pk):
    """
    Return a single event partial for HTMX updates.
    """
    event = get_object_or_404(
        Event.objects.select_related("trip"),
        pk=pk,
        trip__in=accessible_trips_qs(request.user),
    )
    context = {
        "event": event,
    }
    return TemplateResponse(
        request, "trips/includes/day-list-content.html#single_event", context
    )


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


def get_trip_addresses(request):
    """Get addresses from existing events and stays in a trip for transport origin/destination selection."""
    if request.method == "POST":
        trip_id = request.POST.get("trip_id", "").strip()
        field_type = request.POST.get(
            "field_type", ""
        ).strip()  # 'origin' or 'destination'

        if trip_id:
            trip = get_trip_or_404(trip_id, request.user)
            stays_addresses = []
            events_addresses = []

            # Get addresses from stays (always return all stays)
            stays = (
                Stay.objects.filter(days__trip=trip)
                .exclude(address="")
                .exclude(city="")
                .distinct()
                .order_by("name")
            )
            for stay in stays:
                stays_addresses.append(
                    {
                        "name": stay.name,
                        "address": stay.address,
                        "city": stay.city,
                        "type": "stay",
                    }
                )

            # Get addresses from events
            events = (
                Event.objects.filter(trip=trip)
                .exclude(address="")
                .exclude(city="")
                .order_by("name")
            )

            # Track unique events to avoid duplicates
            seen_events = set()
            for event in events:
                # Create a unique key based on name, address, and city
                event_key = (
                    event.name.lower().strip(),
                    event.address.lower().strip(),
                    event.city.lower().strip(),
                )

                if event_key not in seen_events:
                    seen_events.add(event_key)
                    events_addresses.append(
                        {
                            "name": event.name,
                            "address": event.address,
                            "city": event.city,
                            "type": "event",
                        }
                    )

            if stays_addresses or events_addresses:
                return TemplateResponse(
                    request,
                    "trips/includes/trip-address-results.html",
                    {
                        "stays": stays_addresses,
                        "events": events_addresses,
                        "found": True,
                        "field_type": field_type,
                    },
                )

        return TemplateResponse(
            request, "trips/includes/trip-address-results.html", {"found": False}
        )

    return TemplateResponse(
        request, "trips/includes/trip-address-results.html", {"found": False}
    )


def event_notes(request, event_id):
    """
    View or edit the notes for an event (now a field on Event).
    """
    event = get_object_or_404(
        Event, pk=event_id, trip__in=accessible_trips_qs(request.user)
    )
    form = NoteForm(instance=event)
    context = {
        "event": event,
        "form": form,
    }
    return TemplateResponse(request, "trips/event-notes.html", context)


@require_http_methods(["POST"])
def note_create(request, event_id):
    """
    Add or update a note for an event (now a field on Event).
    """
    event = get_object_or_404(
        Event, pk=event_id, trip__in=editable_trips_qs(request.user)
    )
    form = NoteForm(request.POST, instance=event)
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Note added successfully"),
        )
        return HttpResponse(
            status=204, headers={"HX-Trigger": f"eventModified{event.pk}"}
        )
    return HttpResponse(status=400)


def note_modify(request, event_id):
    """
    Modify the note for an event (now a field on Event).
    """
    event = get_object_or_404(
        Event, pk=event_id, trip__in=editable_trips_qs(request.user)
    )
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
        response["HX-Trigger"] = f"eventModified{event.pk}"
        return response
    return TemplateResponse(request, "trips/note-modify.html", context)


def note_delete(request, event_id):
    """
    Delete the note from an event (clear the notes field).
    """
    event = get_object_or_404(
        Event, pk=event_id, trip__in=editable_trips_qs(request.user)
    )
    event.notes = ""
    event.save()
    messages.add_message(
        request,
        messages.ERROR,
        _("Note deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": f"eventModified{event.pk}"})


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
        # Trigger update for all days associated with this stay
        day_triggers = {f"dayModified{day.pk}": {} for day in stay.days.all()}
        return HttpResponse(
            status=204, headers={"HX-Trigger": json.dumps(day_triggers)}
        )
    return HttpResponse(status=400)


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
        # Trigger update for all days associated with this stay
        day_triggers = {f"dayModified{day.pk}": {} for day in stay.days.all()}
        response["HX-Trigger"] = json.dumps(day_triggers)
        return response
    return TemplateResponse(request, "trips/stay-note-modify.html", context)


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
    # Trigger update for all days associated with this stay
    day_triggers = {f"dayModified{day.pk}": {} for day in stay.days.all()}
    return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(day_triggers)})


@require_http_methods(["POST"])
def enrich_stay(request, stay_id):
    """
    Enrich a stay's details using the new Google Places API.
    Shows a preview of enriched data without saving it.
    - Find Place ID using places:searchText.
    - Use Place ID to get details (website, phone, opening hours).
    - Return preview for user confirmation.
    """
    stay = get_object_or_404(
        Stay.objects.filter(days__trip__in=editable_trips_qs(request.user)).distinct(),
        pk=stay_id,
    )
    context = {}

    if not stay.name or not stay.address:
        context["error_message"] = _(
            "Stay must have a name and an address to be enriched."
        )
        context["stay"] = stay
        return TemplateResponse(request, "trips/stay-detail.html", context)

    client = GooglePlacesClient()
    place_id = None
    enriched_data = {}

    try:
        place_id = client.search_place_id(f"{stay.name} {stay.address}")
        if not place_id:
            context["error_message"] = _("Could not find a matching place.")
    except GooglePlacesError as e:
        context["error_message"] = str(e)

    if "error_message" not in context and place_id:
        try:
            details = client.get_place_details(place_id)
            enriched_data = {
                "place_id": details.place_id,
                "website": details.website,
                "phone_number": details.phone_number,
                "opening_hours": details.opening_hours,
            }
        except GooglePlacesError as e:
            context["error_message"] = str(e)

    # Serialize opening_hours to JSON string for form submission
    if enriched_data and enriched_data.get("opening_hours"):
        enriched_data["opening_hours_json"] = json.dumps(enriched_data["opening_hours"])

    # Get first and last day for display
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

    context["stay"] = stay
    context["first_day"] = first_day
    context["last_day"] = last_day
    context["enriched_data"] = enriched_data
    context["show_preview"] = bool(enriched_data and "error_message" not in context)
    return TemplateResponse(request, "trips/stay-enrich-preview.html", context)


@require_http_methods(["POST"])
def confirm_enrich_stay(request, stay_id):
    """
    Confirm and save enriched stay data.
    Receives enriched data from the preview and saves it to the database.
    """
    stay = get_object_or_404(
        Stay.objects.filter(days__trip__in=editable_trips_qs(request.user)).distinct(),
        pk=stay_id,
    )

    # Get enriched data from POST parameters
    place_id = request.POST.get("place_id", "")
    website = request.POST.get("website", "")
    phone_number = request.POST.get("phone_number", "")
    opening_hours_json = request.POST.get("opening_hours", "")

    # Parse opening_hours JSON if present
    opening_hours = None
    if opening_hours_json:
        try:
            opening_hours = json.loads(opening_hours_json)
        except json.JSONDecodeError:
            pass

    # Save the enriched data
    stay.place_id = place_id
    stay.website = website
    stay.phone_number = phone_number
    stay.opening_hours = opening_hours
    stay.enriched = True
    stay.save()

    # Refetch the stay to get the updated data
    stay.refresh_from_db()

    # Get first and last day for display
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

    # Return the updated stay detail view
    context = {
        "stay": stay,
        "first_day": first_day,
        "last_day": last_day,
        "success_message": _("Stay enriched successfully!"),
    }
    response = TemplateResponse(request, "trips/stay-detail.html", context)
    # Trigger update for all days associated with this stay
    day_triggers = {f"dayModified{day.pk}": {} for day in stay.days.all()}
    response["HX-Trigger"] = json.dumps(day_triggers)
    return response


@require_http_methods(["POST"])
def enrich_event(request, event_id):
    """
    Enrich an event's details using the new Google Places API.
    Shows a preview of enriched data without saving it.
    - Find Place ID using places:searchText.
    - Use Place ID to get details (website, phone, opening hours).
    - Return preview for user confirmation.
    """
    qs = Event.objects.select_related("trip__author", "experience", "meal")
    event = get_object_or_404(qs, pk=event_id, trip__in=editable_trips_qs(request.user))
    context = {}

    if not event.name or not event.address:
        context["error_message"] = _(
            "Event must have a name and an address to be enriched."
        )
        event = get_event_instance(event)

        context["event"] = event
        return TemplateResponse(request, "trips/event-detail.html", context)

    client = GooglePlacesClient()
    place_id = None
    enriched_data = {}

    try:
        place_id = client.search_place_id(f"{event.name} {event.address}")
        if not place_id:
            context["error_message"] = _("Could not find a matching place.")
    except GooglePlacesError as e:
        context["error_message"] = str(e)

    if "error_message" not in context and place_id:
        try:
            details = client.get_place_details(place_id)
            enriched_data = {
                "place_id": details.place_id,
                "website": details.website,
                "phone_number": details.phone_number,
                "opening_hours": details.opening_hours,
            }
        except GooglePlacesError as e:
            context["error_message"] = str(e)

    event = get_event_instance(event)

    # Serialize opening_hours to JSON string for form submission
    if enriched_data and enriched_data.get("opening_hours"):
        enriched_data["opening_hours_json"] = json.dumps(enriched_data["opening_hours"])

    context["event"] = event
    context["enriched_data"] = enriched_data
    context["show_preview"] = bool(enriched_data and "error_message" not in context)
    return TemplateResponse(request, "trips/event-enrich-preview.html", context)


@require_http_methods(["POST"])
def confirm_enrich_event(request, event_id):
    """
    Confirm and save enriched event data.
    Receives enriched data from the preview and saves it to the database.
    """
    qs = Event.objects.select_related("trip__author", "experience", "meal")
    event = get_object_or_404(qs, pk=event_id, trip__in=editable_trips_qs(request.user))

    # Get enriched data from POST parameters
    place_id = request.POST.get("place_id", "")
    website = request.POST.get("website", "")
    phone_number = request.POST.get("phone_number", "")
    opening_hours_json = request.POST.get("opening_hours", "")

    # Parse opening_hours JSON if present
    opening_hours = None
    if opening_hours_json:
        try:
            opening_hours = json.loads(opening_hours_json)
        except json.JSONDecodeError:
            pass

    # Save the enriched data
    event.place_id = place_id
    event.website = website
    event.phone_number = phone_number
    event.opening_hours = opening_hours
    event.enriched = True
    event.save()

    # Refetch the event to get the updated data in the child instance
    event.refresh_from_db()
    event = get_event_instance(event)

    # Return the updated event detail view
    context = {
        "event": event,
        "success_message": _("Event enriched successfully!"),
    }
    response = TemplateResponse(request, "trips/event-detail.html", context)
    response["HX-Trigger"] = f"eventModified{event.pk}"
    return response


def search_trip_images(request):
    """HTMX endpoint for searching Unsplash images using destination"""
    if request.method == "POST":
        query = request.POST.get("destination", "").strip()
        trip_id = request.POST.get("trip_id")

        if not query:
            return TemplateResponse(
                request,
                "trips/includes/image-search-results.html",
                {"error": _("Please enter a destination first")},
            )

        # Search Unsplash
        photos = search_unsplash_photos(query, per_page=3)

        if photos is None:
            return TemplateResponse(
                request,
                "trips/includes/image-search-results.html",
                {"error": _("Unsplash API error. Please try again later.")},
            )

        if not photos:
            return TemplateResponse(
                request,
                "trips/includes/image-search-results.html",
                {"error": _("No images found for '{query}'").format(query=query)},
            )

        return TemplateResponse(
            request,
            "trips/includes/image-search-results.html",
            {"photos": photos, "trip_id": trip_id, "query": query},
        )

    return HttpResponse(status=405)


# =============================================================================
# MAIN TRANSFER VIEWS (arrival/departure transfers)
# =============================================================================


def search_airports_view(request):
    """
    HTMX endpoint for airport autocomplete.
    Searches airports by name, city, or IATA code from CSV.
    """
    if request.method == "POST":
        query = request.POST.get("airport_query", "").strip()
        field_type = request.GET.get(
            "field_type", request.POST.get("field_type", "origin")
        )

        if query and len(query) >= 2:
            results = search_airports(query, limit=10)
            if results:
                return TemplateResponse(
                    request,
                    "trips/includes/airport-results.html",
                    {
                        "airports": results,
                        "found": True,
                        "field_type": field_type,
                    },
                )

        return TemplateResponse(
            request,
            "trips/includes/airport-results.html",
            {"found": False, "field_type": field_type},
        )

    return TemplateResponse(
        request,
        "trips/includes/airport-results.html",
        {"found": False, "field_type": "origin"},
    )


def search_stations(request):
    """
    HTMX endpoint for train station autocomplete.
    Searches stations by name or country from CSV.
    """
    if request.method == "POST":
        query = request.POST.get("station_query", "").strip()
        field_type = request.GET.get(
            "field_type", request.POST.get("field_type", "origin")
        )

        if query and len(query) >= 2:
            results = search_train_stations(query, limit=10)
            if results:
                return TemplateResponse(
                    request,
                    "trips/includes/station-results.html",
                    {
                        "stations": results,
                        "found": True,
                        "field_type": field_type,
                    },
                )

        return TemplateResponse(
            request,
            "trips/includes/station-results.html",
            {"found": False, "field_type": field_type},
        )

    return TemplateResponse(
        request,
        "trips/includes/station-results.html",
        {"found": False, "field_type": "origin"},
    )


def arrival_transfer_modal(request, trip_id):
    """Entry point for arrival transfer modal (2-step wizard)."""
    trip = get_trip_or_404(trip_id, request.user)

    # Default transport type to PLANE
    transport_type = MainTransfer.Type.PLANE

    context = {
        "trip": trip,
        "transport_type": transport_type,
    }

    return TemplateResponse(request, "trips/arrival-transfer-modal.html", context)


def departure_transfer_modal(request, trip_id):
    """Entry point for departure transfer modal (2-step wizard)."""
    trip = get_trip_or_404(trip_id, request.user)

    # Default transport type to PLANE
    transport_type = MainTransfer.Type.PLANE

    context = {
        "trip": trip,
        "transport_type": transport_type,
    }

    return TemplateResponse(request, "trips/departure-transfer-modal.html", context)


def main_transfer_step(request, trip_id):
    """HTMX endpoint to load specific step of multi-step modal."""
    trip = get_trip_or_404(trip_id, request.user)
    step = request.GET.get("step", "type")

    # Map string to transport type
    TYPE_MAP = {
        "plane": MainTransfer.Type.PLANE,
        "train": MainTransfer.Type.TRAIN,
        "car": MainTransfer.Type.CAR,
        "other": MainTransfer.Type.OTHER,
    }
    transport_type_param = request.GET.get("transport_type", "plane")
    transport_type = TYPE_MAP.get(transport_type_param, MainTransfer.Type.PLANE)

    # Form mapper
    FORM_MAP = {
        MainTransfer.Type.PLANE: FlightMainTransferForm,
        MainTransfer.Type.TRAIN: TrainMainTransferForm,
        MainTransfer.Type.CAR: CarMainTransferForm,
        MainTransfer.Type.OTHER: OtherMainTransferForm,
    }

    # Get direction from query param (for new separate modals)
    direction_param = request.GET.get("direction", "")

    if step == "type":
        # Determine if this is for departure based on direction parameter
        for_departure = direction_param == "departure"

        context = {
            "trip": trip,
            "transport_type": transport_type,
            "for_departure": for_departure,
            "direction": direction_param,
        }
        return TemplateResponse(
            request, "trips/partials/main-transfer-type.html", context
        )

    elif step in ["arrival", "departure"]:
        # Use direction from query param if present, otherwise infer from step
        if direction_param:
            direction = (
                MainTransfer.Direction.ARRIVAL
                if direction_param == "arrival"
                else MainTransfer.Direction.DEPARTURE
            )
        else:
            direction = (
                MainTransfer.Direction.ARRIVAL
                if step == "arrival"
                else MainTransfer.Direction.DEPARTURE
            )

        instance = MainTransfer.objects.filter(trip=trip, direction=direction).first()
        form_class = FORM_MAP[transport_type]

        # Build home_address and quick_fill_locations for car forms only
        home_address = ""
        quick_fill_locations = []
        if transport_type == MainTransfer.Type.CAR:
            home_address = get_profile(request.user).home_address

            if direction == MainTransfer.Direction.ARRIVAL:
                ref_day = (
                    trip.days.prefetch_related("events", "stay")
                    .order_by("date")
                    .first()
                )
            else:
                ref_day = (
                    trip.days.prefetch_related("events", "stay")
                    .order_by("-date")
                    .first()
                )

            if ref_day:
                if hasattr(ref_day, "stay") and ref_day.stay and ref_day.stay.address:
                    quick_fill_locations.append(
                        {
                            "label": ref_day.stay.name,
                            "address": ref_day.stay.address,
                            "type": "stay",
                        }
                    )
                for event in ref_day.events.order_by("order", "pk"):
                    if event.address:
                        event_type = (
                            "meal"
                            if event.category == Event.Category.MEAL
                            else "experience"
                        )
                        quick_fill_locations.append(
                            {
                                "label": event.name,
                                "address": event.address,
                                "type": event_type,
                            }
                        )

            if not quick_fill_locations:
                quick_fill_locations = [
                    {
                        "label": trip.destination,
                        "address": trip.destination,
                        "type": "destination",
                    }
                ]

        form = form_class(
            instance=instance,
            trip=trip,
            autocomplete=True,
            home_address=home_address,
            initial={"direction": direction},
        )

        # Check if form was pre-filled from arrival
        prefilled = getattr(form, "prefilled_from_arrival", False)

        context = {
            "trip": trip,
            "form": form,
            "step": step,
            "transport_type": transport_type,
            "direction": "arrival" if step == "arrival" else "departure",
            "prefilled_from_arrival": prefilled,
            "quick_fill_locations": quick_fill_locations,
        }

        template_map = {
            MainTransfer.Type.PLANE: "trips/partials/main-transfer-flight.html",
            MainTransfer.Type.TRAIN: "trips/partials/main-transfer-train.html",
            MainTransfer.Type.CAR: "trips/partials/main-transfer-car.html",
            MainTransfer.Type.OTHER: "trips/partials/main-transfer-other.html",
        }

        return TemplateResponse(request, template_map[transport_type], context)

    return HttpResponse("Invalid step", status=400)


def save_main_transfer(request, trip_id):
    """Save main transfer (arrival or departure)."""
    trip = get_trip_for_editor_or_404(trip_id, request.user)

    if request.method != "POST":
        return HttpResponse(status=405)

    # Get transport_type and direction from query params
    TYPE_MAP = {
        "plane": MainTransfer.Type.PLANE,
        "train": MainTransfer.Type.TRAIN,
        "car": MainTransfer.Type.CAR,
        "other": MainTransfer.Type.OTHER,
    }
    transport_type_param = request.GET.get("transport_type", "plane")
    transport_type = TYPE_MAP.get(transport_type_param, MainTransfer.Type.PLANE)

    direction_param = request.GET.get("direction", "arrival")
    direction = (
        MainTransfer.Direction.ARRIVAL
        if direction_param == "arrival"
        else MainTransfer.Direction.DEPARTURE
    )

    FORM_MAP = {
        MainTransfer.Type.PLANE: FlightMainTransferForm,
        MainTransfer.Type.TRAIN: TrainMainTransferForm,
        MainTransfer.Type.CAR: CarMainTransferForm,
        MainTransfer.Type.OTHER: OtherMainTransferForm,
    }

    form_class = FORM_MAP[transport_type]
    instance = MainTransfer.objects.filter(trip=trip, direction=direction).first()
    form = form_class(
        request.POST, instance=instance, trip=trip, autocomplete=False, home_address=""
    )

    if form.is_valid():
        transfer = form.save(commit=False)
        transfer.trip = trip
        transfer.type = transport_type
        transfer.direction = direction
        if not instance:
            transfer.last_modified_by = request.user
        transfer.save()

        # Always close modal and refresh trip
        message = str(_("Transfer saved successfully!"))
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "tripModified": {},
                        "hide-modal": {},
                        "showMessage": {
                            "type": "success",
                            "message": message,
                        },
                    }
                )
            },
        )

    # Return form with errors
    context = {
        "trip": trip,
        "form": form,
        "transport_type": transport_type,
        "direction": direction_param,
    }

    template_map = {
        MainTransfer.Type.PLANE: "trips/partials/main-transfer-flight.html",
        MainTransfer.Type.TRAIN: "trips/partials/main-transfer-train.html",
        MainTransfer.Type.CAR: "trips/partials/main-transfer-car.html",
        MainTransfer.Type.OTHER: "trips/partials/main-transfer-other.html",
    }

    return TemplateResponse(request, template_map[transport_type], context)


# ── SHARING VIEWS ─────────────────────────────────────────────────────────────


@login_not_required
def shared_trip_detail(request, token):
    """Public read-only view for a shared trip. No login required."""
    link = get_object_or_404(ShareLink, id=token)

    if not link.is_valid:
        if link.expires_at:
            return TemplateResponse(request, "trips/link-expired.html", status=410)
        return TemplateResponse(request, "trips/link-revoked.html", status=410)

    days = link.trip.days.prefetch_related(
        Prefetch(
            "events",
            queryset=Event.objects.all().order_by("order", "pk"),
        ),
        Prefetch(
            "stay",
            queryset=Stay.objects.select_related("author"),
        ),
    ).order_by("date")

    context = {
        "trip": link.trip,
        "days": days,
        "is_shared_view": True,
        "permission_level": link.permission_level,
    }
    return TemplateResponse(request, "trips/shared-trip-detail.html", context)


def share_link_create(request, trip_id):
    """Create a new share link for a trip (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)

    created_link = None
    if request.method == "POST":
        form = ShareLinkCreateForm(request.POST)
        if form.is_valid():
            created_link = form.save(trip=trip, created_by=request.user)
            form = ShareLinkCreateForm()
    else:
        form = ShareLinkCreateForm()

    links = trip.share_links.filter(is_active=True).order_by("-created_at")
    return TemplateResponse(
        request,
        "trips/share-link-modal.html",
        {"form": form, "trip": trip, "links": links, "created_link": created_link},
    )


def share_link_list(request, trip_id):
    """List active share links for a trip (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    links = trip.share_links.filter(is_active=True).order_by("-created_at")
    return TemplateResponse(
        request,
        "trips/share-link-list.html",
        {"trip": trip, "links": links},
    )


@require_http_methods(["POST"])
def share_link_revoke(request, link_id):
    """Deactivate a share link (owner only)."""
    link = get_object_or_404(ShareLink, id=link_id, trip__author=request.user)
    link.is_active = False
    link.save(update_fields=["is_active"])
    trip = link.trip
    links = trip.share_links.filter(is_active=True).order_by("-created_at")
    return TemplateResponse(
        request,
        "trips/share-link-modal.html",
        {
            "form": ShareLinkCreateForm(),
            "trip": trip,
            "links": links,
            "created_link": None,
        },
    )


def search_user_by_email(request, trip_id):
    """HTMX: search registered user by email to invite as collaborator (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    email = request.GET.get("collab_email", "").strip()
    User = get_user_model()

    if not email:
        return HttpResponse("")

    existing_ids = set(trip.collaborators.values_list("id", flat=True))
    existing_ids.add(trip.author_id)

    # Use partial matching (case-insensitive) for email search
    matching_users = User.objects.filter(email__icontains=email)[:10]

    results = []
    for user in matching_users:
        already_collab = user.id in existing_ids
        results.append(
            {
                "user": user,
                "already_collab": already_collab,
            }
        )

    return TemplateResponse(
        request,
        "trips/includes/collab-search-result.html",
        {"trip": trip, "results": results, "email": email},
    )


@require_http_methods(["POST"])
def add_collaborator(request, trip_id):
    """Add a registered user as collaborator (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    User = get_user_model()
    email = request.POST.get("email", "").strip()
    can_edit = request.POST.get("can_edit", "true").lower() != "false"

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return HttpResponse(status=400)

    if user == trip.author or trip.collaborators.filter(pk=user.pk).exists():
        return HttpResponse(status=400)

    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.create(
        trip=trip, user=user, color=color, added_by=request.user, can_edit=can_edit
    )

    trip_url = request.build_absolute_uri(reverse("trips:trip-detail", args=[trip.pk]))
    context = {"trip": trip, "added_by": request.user, "trip_url": trip_url}
    recipient_language = getattr(user.profile, "language", "it")
    with translation_override(recipient_language):
        subject = render_to_string(
            "trips/email/added_as_collaborator_subject.txt", context
        ).strip()
        text_body = render_to_string(
            "trips/email/added_as_collaborator_body.txt", context
        )
        html_body = render_to_string(
            "trips/email/added_as_collaborator_body.html", context
        )
    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def toggle_participant_role(request, trip_id, collaboration_id):
    """Downgrade editor to viewer (owner only). Upgrade is not allowed via this view."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    collaboration = get_object_or_404(TripCollaboration, pk=collaboration_id, trip=trip)
    if not collaboration.can_edit:
        return HttpResponse(status=400)
    collaboration.can_edit = False
    collaboration.save()
    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def add_viewer_by_email(request, trip_id):
    """Add a viewer by email — sends a permanent share link (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    User = get_user_model()
    email = request.POST.get("email", "").strip()

    if not email:
        return HttpResponse(status=400)

    if trip.collaborations.filter(participant_email=email).exists():
        return HttpResponse(status=400)

    share_link = ShareLink.objects.create(
        trip=trip,
        created_by=request.user,
        permission_level=ShareLink.PermissionLevel.VIEW,
        expires_at=None,
        label=email,
    )

    color = TripCollaboration.next_free_color(trip)
    try:
        user = User.objects.get(email=email)
        if trip.collaborators.filter(pk=user.pk).exists() or user == trip.author:
            share_link.delete()
            return HttpResponse(status=400)
        TripCollaboration.objects.create(
            trip=trip,
            user=user,
            color=color,
            added_by=request.user,
            can_edit=False,
            share_link=share_link,
        )
    except User.DoesNotExist:
        TripCollaboration.objects.create(
            trip=trip,
            user=None,
            participant_email=email,
            color=color,
            added_by=request.user,
            can_edit=False,
            share_link=share_link,
        )

    share_url = request.build_absolute_uri(share_link.get_absolute_url())
    context = {"trip": trip, "invited_by": request.user, "share_url": share_url}
    sender_language = getattr(request.user.profile, "language", "it")
    with translation_override(sender_language):
        subject = render_to_string(
            "trips/email/viewer_invitation_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/viewer_invitation_body.txt", context)
        html_body = render_to_string("trips/email/viewer_invitation_body.html", context)
    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def add_named_participant(request, trip_id):
    """Add a named participant with no account or email (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    name = request.POST.get("name", "").strip()

    if not name:
        return HttpResponse(status=400)

    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.create(
        trip=trip,
        user=None,
        participant_name=name,
        color=color,
        added_by=request.user,
        can_edit=False,
    )

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


@require_http_methods(["POST"])
def remove_collaborator(request, trip_id, collaboration_id):
    """Remove a collaborator from a trip (owner only, data is preserved)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    collaboration = get_object_or_404(TripCollaboration, pk=collaboration_id, trip=trip)
    collaboration.delete()

    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal-list.html",
        {"trip": trip, "collaborations": collaborations},
        headers={"HX-Trigger": "collaboratorsModified"},
    )


def collaborators_modal(request, trip_id):
    """GET: render the collaborators management modal (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-modal.html",
        {"trip": trip, "collaborations": collaborations},
    )


def collab_inline(request, trip_id):
    """GET: render the compact inline collaborators row (HTMX refresh)."""
    trip = get_trip_or_404(trip_id, request.user)
    collaborations = trip.collaborations.select_related("user__profile").all()
    return TemplateResponse(
        request,
        "trips/includes/collab-inline.html",
        {"trip": trip, "collaborations": collaborations},
    )


@require_http_methods(["POST"])
def invite_collaborator(request, trip_id):
    """Invite a non-registered user by email (owner only)."""
    trip = get_trip_for_owner_or_404(trip_id, request.user)
    User = get_user_model()
    email = request.POST.get("email", "").strip()

    if User.objects.filter(email=email).exists():
        return HttpResponse(status=400)

    invitation = TripInvitation.objects.create(
        trip=trip,
        email=email,
        invited_by=request.user,
        expires_at=timezone.now() + timezone.timedelta(days=7),
    )

    accept_url = request.build_absolute_uri(invitation.get_absolute_url())
    context = {"trip": trip, "invited_by": request.user, "accept_url": accept_url}
    sender_language = getattr(request.user.profile, "language", "it")
    with translation_override(sender_language):
        subject = render_to_string(
            "trips/email/invitation_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/invitation_body.txt", context)
        html_body = render_to_string("trips/email/invitation_body.html", context)
    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    return TemplateResponse(
        request,
        "trips/includes/collab-invite-sent.html",
        {"email": email},
    )


@login_not_required
def accept_invitation(request, token):
    """Accept a trip collaboration invitation via token."""
    invitation = get_object_or_404(TripInvitation, token=token)

    if not invitation.is_valid:
        return HttpResponse(status=400)

    if not request.user.is_authenticated:
        signup_url = reverse("account_signup")
        accept_url = reverse("trips:accept-invitation", kwargs={"token": token})
        request.session["invitation_token"] = str(token)
        return redirect(f"{signup_url}?next={accept_url}")

    invitation.is_accepted = True
    invitation.accepted_at = timezone.now()
    invitation.save()

    trip = invitation.trip
    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.get_or_create(
        trip=trip,
        user=request.user,
        defaults={"color": color, "added_by": invitation.invited_by, "can_edit": False},
    )

    trip_url = request.build_absolute_uri(reverse("trips:trip-detail", args=[trip.pk]))
    context = {
        "trip": trip,
        "new_collaborator_email": request.user.email,
        "trip_url": trip_url,
    }
    owner_language = getattr(invitation.invited_by.profile, "language", "it")
    with translation_override(owner_language):
        subject = render_to_string(
            "trips/email/invitation_accepted_subject.txt", context
        ).strip()
        text_body = render_to_string(
            "trips/email/invitation_accepted_body.txt", context
        )
        html_body = render_to_string(
            "trips/email/invitation_accepted_body.html", context
        )
    msg = EmailMultiAlternatives(
        subject=subject, body=text_body, to=[invitation.invited_by.email]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    messages.success(request, _("You've joined the trip as a participant."))
    return redirect(reverse("trips:trip-detail", args=[trip.pk]))


# ──────────────────────────────────────────────────────────────
# Unified Trip Map (Leaflet + Google Places + HTMX)
# ──────────────────────────────────────────────────────────────


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


def _build_map_json(days_with_events, unassigned_events):
    """
    Serialize all map items to a JSON-safe list for the Leaflet JS module.
    Each item has: kind, name, address, lat, lng, day_index (0=unassigned).
    """
    items = []
    seen_stay_pks = set()

    for idx, day_data in enumerate(days_with_events, start=1):
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
                }
            )

    return items


def trip_map(request, pk):
    """Unified interactive map for a trip: all events across all days + unassigned."""
    trip = get_object_or_404(
        Trip.objects.prefetch_related("collaborations"),
        pk=pk,
    )
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404

    days_with_events, unassigned_events = _build_map_events_context(trip)
    map_items = _build_map_json(days_with_events, unassigned_events)
    return TemplateResponse(
        request,
        "trips/trip-map.html",
        {
            "trip": trip,
            "days_with_events": days_with_events,
            "unassigned_events": unassigned_events,
            "map_items_json": json.dumps(map_items),
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
    return TemplateResponse(
        request,
        "trips/includes/events-list-fragment.html",
        {"trip": trip, "unpaired_events": unpaired_events, "day_groups": day_groups},
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
        selected_pks = {int(pk) for pk in request.POST.getlist("days")}
        if destination and selected_pks:
            valid_pks = selected_pks - custom_day_pks
            Day.objects.filter(pk__in=valid_pks, trip=trip).update(
                destination=destination,
            )
            affected_numbers = list(
                Day.objects.filter(pk__in=valid_pks, trip=trip).values_list(
                    "number", flat=True
                )
            )
            for pk in valid_pks:
                async_task("trips.tasks.calculate_day_transfer", pk)
            for number in affected_numbers:
                prev = Day.objects.filter(trip=trip, number=number - 1).first()
                if prev:
                    async_task("trips.tasks.calculate_day_transfer", prev.pk)
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
            affected_pks = list(stage_days.values_list("pk", flat=True))
            affected_numbers = list(stage_days.values_list("number", flat=True))
            for day in stage_days:
                day.events.update(day=None)
            stage_days.update(destination=trip.destination)
            for pk in affected_pks:
                async_task("trips.tasks.calculate_day_transfer", pk)
            for number in affected_numbers:
                prev = Day.objects.filter(trip=trip, number=number - 1).first()
                if prev:
                    async_task("trips.tasks.calculate_day_transfer", prev.pk)
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
        radius = min(max(max_dist * 1.5, 10_000), 500_000)
        return clat, clng, radius
    # Fallback: geocode the trip destination
    if trip.destination:
        g = geocoder.mapbox(trip.destination, key=settings.MAPBOX_ACCESS_TOKEN)
        if g.latlng:
            return g.latlng[0], g.latlng[1], 50_000
    return None


@require_http_methods(["POST"])
def map_search(request, pk):
    """HTMX endpoint: search Google Places and return results partial."""
    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404

    query = request.POST.get("query", "").strip()
    results = []
    error = None

    if query:
        client = GooglePlacesClient()
        try:
            results = client.search_text(query, location_bias=_trip_location_bias(trip))
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
        event = Event(
            trip=trip,
            name=name,
            address=address,
            place_id=place_id,
            category=category,
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
