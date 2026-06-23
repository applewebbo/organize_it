import json
import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from accounts.models import get_profile
from trips.models import (
    Day,
    Event,
    Stay,
    TripCollaboration,
)
from trips.utils import accessible_trips_qs, create_day_map, editable_trips_qs

logger = logging.getLogger(__name__)


def _day_city(day):
    """Return the relevant city for a day: stage destination if set, else trip destination."""
    return day.destination or day.trip.destination


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
    profile = get_profile(request.user)
    if force_view in ["list", "map"]:
        show_map = force_view == "map"
    else:
        show_map = profile.default_map_view == "map"

    next_day = day.next_day

    context = {
        "day": day,
        "show_map": show_map,
        "next_day": next_day,
        "show_weather": profile.show_weather,
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


@require_http_methods(["POST"])
def reorder_events(request, day_id):
    """Save new event order after drag & drop. Expects JSON body: {"order": [pk1, pk2, ...]}"""
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


@require_http_methods(["POST"])
def move_event_to_day(request, event_id, day_id):
    """Move a paired event to a different day (cross-day drag & drop or mobile button)."""
    event = get_object_or_404(
        Event,
        pk=event_id,
        day__isnull=False,
        trip__in=editable_trips_qs(request.user),
    )
    old_day_pk = event.day_id
    new_day = get_object_or_404(Day, pk=day_id, trip=event.trip)

    if old_day_pk == new_day.pk:
        return HttpResponse(status=204)

    event.day = new_day
    event.order = Event.objects.filter(day=new_day).count()
    event.save(update_fields=["day", "order"])

    messages.add_message(request, messages.SUCCESS, _("Event moved successfully"))
    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps(
                {
                    f"dayModified{old_day_pk}": True,
                    f"dayModified{new_day.pk}": True,
                }
            )
        },
    )


@require_http_methods(["GET"])
def move_event_day_modal(request, event_id):
    """Mobile: show day picker to move a paired event to a different day."""
    event = get_object_or_404(
        Event,
        pk=event_id,
        day__isnull=False,
        trip__in=editable_trips_qs(request.user),
    )
    days = event.trip.days.exclude(pk=event.day_id).order_by("number")
    return TemplateResponse(
        request,
        "trips/move-event-day-modal.html",
        {"event": event, "days": days},
    )
