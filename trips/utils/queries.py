from django.db.models import Max, Min, Prefetch, Q
from django.shortcuts import get_object_or_404

from accounts.models import get_profile
from trips.models import Event, Stay, Trip
from trips.utils.stages import group_days_by_destination
from trips.utils.transport import get_flight_origin_icao


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

    # Abandoned wizard draft (author's own, not yet completed), surfaced so the
    # home page can offer to resume or discard it.
    wizard_draft = (
        Trip.objects.filter(author=user, wizard_completed=False)
        .order_by("-wizard_started_at")
        .first()
    )

    # Base queryset: owned + collaborated trips excluding archived and drafts
    base_qs = (
        Trip.objects.filter(Q(author=user) | Q(collaborators=user))
        .exclude(status=Trip.Status.ARCHIVED)
        .filter(wizard_completed=True)
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
        "wizard_draft": wizard_draft,
    }
