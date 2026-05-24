import json
import logging

from django.contrib import messages
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from trips.forms import ExperienceForm, MealForm, NoteForm
from trips.models import Day, Event
from trips.services import GooglePlacesClient, GooglePlacesError
from trips.utils import (
    accessible_trips_qs,
    editable_trips_qs,
    get_event_instance,
    get_trip_for_editor_or_404,
    get_trip_stages,
)
from trips.views.days import _day_city

logger = logging.getLogger(__name__)


def add_experience(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__in=editable_trips_qs(request.user))
    unpaired_experiences = Event.objects.filter(
        day__isnull=True, trip=day.trip, category=2
    )
    form = ExperienceForm(
        request.POST or None, initial={"city": _day_city(day)}, geocode=True
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
        request.POST or None, initial={"city": _day_city(day)}, geocode=True
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
    stages = get_trip_stages(trip)
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
    context = {"form": form, "trip": trip, "stages": stages}
    return TemplateResponse(request, "trips/experience-create-unpaired.html", context)


def add_meal_to_trip(request, trip_pk):
    trip = get_trip_for_editor_or_404(trip_pk, request.user)
    stages = get_trip_stages(trip)
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
    context = {"form": form, "trip": trip, "stages": stages}
    return TemplateResponse(request, "trips/meal-create-unpaired.html", context)


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
    qs = Event.objects.select_related("trip__author", "day")
    event = get_object_or_404(qs, pk=pk, trip__in=editable_trips_qs(request.user))
    day_pk = event.day_id
    event.city = event.day.destination or event.trip.destination
    event.day = None
    event.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Event unpaired successfully"),
    )
    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps(
                {
                    "unpairedModified": True,
                    f"dayModified{day_pk}": True,
                    "hide-modal": True,
                }
            )
        },
    )


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
    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps(
                {
                    "unpairedModified": True,
                    f"dayModified{day.pk}": True,
                    "hide-modal": True,
                }
            )
        },
    )


def event_pair_choice(request, pk):
    """
    Provide a list of days to pair with the selected event.
    If the event has a city matching a trip stage, only days from that stage are shown.
    """
    event = get_object_or_404(Event, pk=pk, trip__in=accessible_trips_qs(request.user))
    trip = event.trip
    if event.city:
        if event.city == trip.destination:
            days = trip.days.filter(
                models.Q(destination=event.city) | models.Q(destination="")
            )
        else:
            days = trip.days.filter(destination=event.city)
    else:
        days = trip.days.all()

    context = {
        "event": event,
        "days": days,
    }
    return TemplateResponse(request, "trips/event-pair-choice.html", context)


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


def tag_suggestions(request):
    """HTMX: return existing tags for autocomplete."""
    q = request.GET.get("tag", "").strip()
    tags_qs = (
        Event.objects.filter(trip__in=accessible_trips_qs(request.user))
        .exclude(tag="")
        .values_list("tag", flat=True)
        .distinct()
        .order_by("tag")
    )
    if q:
        tags_qs = tags_qs.filter(tag__icontains=q)
    return TemplateResponse(
        request,
        "trips/includes/tag-results.html",
        {"tags": list(tags_qs[:10])},
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
