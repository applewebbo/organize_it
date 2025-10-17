from datetime import date, timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic import View

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
from trips.utils import (
    annotate_event_overlaps,
    convert_google_opening_hours,
    create_day_map,
    geocode_location,
    get_event_instance,
    get_trips,
)


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
        request.POST or None, initial={"city": day.trip.destination}, geocode=True
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
        request.POST or None, initial={"city": day.trip.destination}, geocode=True
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
        data=request.POST or None,
        initial={"apply_to_days": [day_id], "city": trip.destination},
        geocode=True,
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

    event = get_event_instance(event)

    context = {
        "event": event,
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

    event = get_event_instance(event)

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
        context = {
            "event": event,
            "category": event.category,
        }
        response = TemplateResponse(request, "trips/event-detail.html", context)
        response["HX-Trigger"] = f"eventModified{event.pk}"
        return response
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
def single_event(request, pk):
    """
    Return a single event partial for HTMX updates.
    """
    event = get_object_or_404(Event, pk=pk, day__trip__author=request.user)
    context = {
        "event": event,
    }
    return TemplateResponse(request, "trips/includes/day.html#single_event", context)


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


@login_required
@require_http_methods(["POST"])
def enrich_stay(request, stay_id):
    """
    Enrich a stay's details using the new Google Places API.
    - Find Place ID using places:searchText.
    - Use Place ID to get details (website, phone, opening hours).
    - Update the stay instance.
    """
    stay = get_object_or_404(
        Stay.objects.filter(days__trip__author=request.user).distinct(), pk=stay_id
    )
    context = {}

    if not stay.name or not stay.address:
        messages.error(
            request, _("Stay must have a name and an address to be enriched.")
        )
        return HttpResponse(status=400)

    api_key = settings.GOOGLE_PLACES_API_KEY

    if not api_key:
        context["error_message"] = _("Google Places API key is not configured.")
    else:
        # 1. Find Place ID
        search_url = "https://places.googleapis.com/v1/places:searchText"
        search_payload = {"textQuery": f"{stay.name} {stay.address}"}
        search_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id",
        }

        try:
            response = requests.post(
                search_url, json=search_payload, headers=search_headers, timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if data.get("places"):
                stay.place_id = data["places"][0]["id"]
            else:
                context["error_message"] = _("Could not find a matching place.")

        except requests.exceptions.Timeout:
            context["error_message"] = _("Google Places API request timed out.")
        except requests.RequestException as e:
            error_message = f"Error calling Google Places API: {e}"
            if e.response is not None:
                error_message = f"API Error: {e.response.text}"
            context["error_message"] = error_message

    if "error_message" not in context and stay.place_id:
        # 2. Get Place Details
        details_url = f"https://places.googleapis.com/v1/places/{stay.place_id}"
        details_headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "websiteUri,internationalPhoneNumber,regularOpeningHours",
        }

        try:
            response = requests.get(details_url, headers=details_headers, timeout=5)
            response.raise_for_status()
            data = response.json()

            stay.website = data.get("websiteUri", "")
            stay.phone_number = data.get("internationalPhoneNumber", "")
            google_opening_hours = data.get("regularOpeningHours", None)
            stay.opening_hours = convert_google_opening_hours(google_opening_hours)
            stay.enriched = True
            stay.save()

            messages.success(request, _("Stay enriched successfully!"))

        except requests.exceptions.Timeout:
            context["error_message"] = _("Google Places API request timed out.")
        except requests.RequestException as e:
            error_message = f"Error calling Google Places API: {e}"
            if e.response is not None:
                error_message = f"API Error: {e.response.text}"
            context["error_message"] = error_message

    # Refetch the stay to get the updated data
    stay.refresh_from_db()

    context["stay"] = stay
    context["success_message"] = _("Stay enriched successfully!")
    return TemplateResponse(request, "trips/stay-detail.html", context)


class DayMapView(View):
    @method_decorator(login_required, name="dispatch")
    def dispatch(self, request, day_id, *args, **kwargs):
        self.day_obj = get_object_or_404(Day, pk=day_id, trip__author=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        events = self.day_obj.events.exclude(category=1)
        stay = self.day_obj.stay
        next_day = self.day_obj.next_day
        prev_day = self.day_obj.prev_day
        next_day_stay = None
        if next_day and next_day.stay and next_day.stay != stay:
            next_day_stay = next_day.stay
        is_last_day = not next_day
        locations = {
            "stay": stay,
            "events": events,
            "next_day_stay": next_day_stay,
            "last_day": is_last_day,
        }
        if not (prev_day and prev_day.stay and prev_day.stay == stay):
            locations["first_day"] = True

        # Filter out events without latitude or longitude
        events_with_location = events.filter(
            latitude__isnull=False, longitude__isnull=False
        )

        map = create_day_map(events_with_location, stay, next_day_stay)

        context = {"map": map, "day": self.day_obj, "locations": locations}
        return TemplateResponse(request, "trips/day-map.html", context)


@login_required
@require_http_methods(["POST"])
def enrich_event(request, event_id):
    """
    Enrich an event's details using the new Google Places API.
    - Find Place ID using places:searchText.
    - Use Place ID to get details (website, phone, opening hours).
    - Update the event instance.
    """
    qs = Event.objects.select_related("trip__author", "transport", "experience", "meal")
    event = get_object_or_404(qs, pk=event_id, trip__author=request.user)
    context = {}

    if not event.name or not event.address:
        context["error_message"] = _(
            "Event must have a name and an address to be enriched."
        )
        event = get_event_instance(event)

        context["event"] = event
        return TemplateResponse(request, "trips/event-detail.html", context)

    api_key = settings.GOOGLE_PLACES_API_KEY

    if not api_key:
        context["error_message"] = _("Google Places API key is not configured.")
    else:
        # 1. Find Place ID
        search_url = "https://places.googleapis.com/v1/places:searchText"
        search_payload = {"textQuery": f"{event.name} {event.address}"}
        search_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id",
        }

        try:
            response = requests.post(
                search_url, json=search_payload, headers=search_headers, timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if data.get("places"):
                event.place_id = data["places"][0]["id"]
            else:
                context["error_message"] = _("Could not find a matching place.")

        except requests.exceptions.Timeout:
            context["error_message"] = _("Google Places API request timed out.")
        except requests.RequestException as e:
            error_message = f"Error calling Google Places API: {e}"
            if e.response is not None:
                error_message = f"API Error: {e.response.text}"
            context["error_message"] = error_message

    if "error_message" not in context and event.place_id:
        # 2. Get Place Details
        details_url = f"https://places.googleapis.com/v1/places/{event.place_id}"
        details_headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "websiteUri,internationalPhoneNumber,regularOpeningHours",
        }

        try:
            response = requests.get(details_url, headers=details_headers, timeout=5)
            response.raise_for_status()
            data = response.json()

            event.website = data.get("websiteUri", "")
            event.phone_number = data.get("internationalPhoneNumber", "")
            google_opening_hours = data.get("regularOpeningHours", None)
            event.opening_hours = convert_google_opening_hours(google_opening_hours)
            event.enriched = True
            event.save()

            messages.success(request, _("Event enriched successfully!"))

        except requests.exceptions.Timeout:
            context["error_message"] = _("Google Places API request timed out.")
        except requests.RequestException as e:
            error_message = f"Error calling Google Places API: {e}"
            if e.response is not None:
                error_message = f"API Error: {e.response.text}"
            context["error_message"] = error_message

    # Refetch the event to get the updated data in the child instance
    event.refresh_from_db()

    event = get_event_instance(event)

    context["event"] = event
    context["success_message"] = _("Event enriched successfully!")
    return TemplateResponse(request, "trips/event-detail.html", context)
