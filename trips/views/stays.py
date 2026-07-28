import json
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from trips.forms import AddNoteToStayForm, StayForm
from trips.models import Day, Stay, StayBooking
from trips.services import GooglePlacesClient, GooglePlacesError
from trips.utils import (
    build_stay22_url,
    editable_trips_qs,
    get_trip_for_editor_or_404,
    get_trip_or_404,
    get_trip_stages,
)
from trips.views.days import _day_city

logger = logging.getLogger(__name__)


def add_stay_for_trip(request, trip_pk):
    trip = get_trip_for_editor_or_404(trip_pk, request.user)
    # Mirror the Stay22 'Find a stay' flow (#405): a multi-stage trip first
    # picks a leg, then the form is pre-filled with that stage's city and days
    # so the user only enters the accommodation name/address.
    stages = get_trip_stages(trip)
    destination = request.GET.get("destination")
    if request.method == "GET" and destination is None and len(stages) > 1:
        context = {"trip": trip, "stages": stages}
        return TemplateResponse(
            request, "trips/includes/add-stay-stage-chooser.html", context
        )
    if destination is None:
        destination = stages[0]["destination"]
    stage = _get_stage(trip, destination)
    initial = {
        "city": destination,
        "apply_to_days": [day.pk for day in stage["days"]],
    }
    form = StayForm(
        trip,
        data=request.POST or None,
        initial=initial,
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
        initial={"apply_to_days": [day_id], "city": _day_city(day)},
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


def _get_stage(trip, destination):
    """Return the trip stage matching ``destination``, else raise Http404."""
    for stage in get_trip_stages(trip):
        if stage["destination"] == destination:
            return stage
    raise Http404


def _booking_content_context(trip, destination, user):
    """Build context for the booking content fragment, ensuring a booking exists."""
    stage = _get_stage(trip, destination)
    collaborations = trip.collaborations.all()
    booking, created = StayBooking.objects.get_or_create(
        trip=trip, destination=destination, created_by=user
    )
    if created:
        booking.participants.set(collaborations)
    selected_ids = set(booking.participants.values_list("pk", flat=True))
    days = stage["days"]
    return {
        "trip": trip,
        "destination": destination,
        "booking": booking,
        "collaborations": collaborations,
        "selected_ids": selected_ids,
        "includes_author": booking.includes_author,
        "provider_choices": StayBooking.Provider.choices,
        "checkin": days[0].date,
        "checkout": days[-1].date,
    }


def stay_booking_modal(request, trip_pk):
    if not settings.STAY22_AID:
        raise Http404
    trip = get_trip_or_404(trip_pk, request.user)
    stages = get_trip_stages(trip)
    destination = request.GET.get("destination")
    if destination is None and len(stages) > 1:
        context = {"trip": trip, "stages": stages}
        return TemplateResponse(
            request, "trips/includes/stay-booking-stage-chooser.html", context
        )
    if destination is None:
        destination = stages[0]["destination"]
    context = _booking_content_context(trip, destination, request.user)
    return TemplateResponse(request, "trips/includes/stay-booking-modal.html", context)


@require_http_methods(["POST"])
def stay_booking_save(request, trip_pk):
    if not settings.STAY22_AID:
        raise Http404
    trip = get_trip_or_404(trip_pk, request.user)
    destination = request.POST.get("destination")
    _get_stage(trip, destination)
    booking, _ = StayBooking.objects.get_or_create(
        trip=trip, destination=destination, created_by=request.user
    )
    booking.includes_author = "includes_author" in request.POST
    provider = request.POST.get("provider")
    if provider in StayBooking.Provider.values:
        booking.provider = provider
    booking.save()
    ids = request.POST.getlist("participants")
    booking.participants.set(trip.collaborations.filter(pk__in=ids))
    context = _booking_content_context(trip, destination, request.user)
    return TemplateResponse(
        request, "trips/includes/stay-booking-content.html", context
    )


def stay_booking_redirect(request, trip_pk):
    if not settings.STAY22_AID:
        raise Http404
    trip = get_trip_or_404(trip_pk, request.user)
    destination = request.GET.get("destination") or trip.destination
    stage = _get_stage(trip, destination)
    booking = get_object_or_404(
        StayBooking, trip=trip, destination=destination, created_by=request.user
    )
    days = stage["days"]
    url = build_stay22_url(
        aid=settings.STAY22_AID,
        address=destination,
        checkin=days[0].date,
        checkout=days[-1].date,
        adults=booking.adults,
        children=booking.children,
        provider=booking.provider,
    )
    return HttpResponseRedirect(url)
