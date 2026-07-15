import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import get_profile
from suggestions.ai.base import AISuggestionError
from suggestions.forms import (
    AICredentialsForm,
    AISuggestionsToggleForm,
    SuggestionPreferencesForm,
)
from suggestions.models import (
    AICredentials,
    SharedKeyNoticeDismissal,
    SuggestionPreferences,
)
from suggestions.services import (
    DAY_STRATEGIES,
    DAY_STRATEGY_ADD,
    DAY_STRATEGY_DELETE,
    DAY_STRATEGY_UNPAIR,
    generate_day_itinerary,
    generate_suggestions,
    get_cached_suggestions,
)
from trips.models import Day, Event, Stay, Trip
from trips.services import GooglePlacesClient, GooglePlacesError
from trips.utils import accessible_trips_qs, build_categorized_event, get_trip_stages
from trips.views.maps import _build_map_events_context

# Both the desktop map panel and the mobile modal accept a suggestion through
# these endpoints: the accepted card is replaced by a success message, and the
# map events panel is refreshed out-of-band on the desktop.
_ACCEPT_URL = {
    "experience": "suggestions:accept-experience",
    "meal": "suggestions:accept-meal",
    "stay": "suggestions:accept-stay",
}
_ACCEPT_CATEGORY = {
    "experience": Event.Category.EXPERIENCE,
    "meal": Event.Category.MEAL,
}
# Per-kind icon + colour, matching the project's "Add event" dropdown / map pins.
_KIND_ICON = {
    "experience": ("ph-map-pin", "text-green-500"),
    "meal": ("ph-fork-knife", "text-yellow-500"),
    "stay": ("ph-bed", "text-sky-500"),
}


def _added_keys(trip, user) -> tuple[set, set]:
    """Collect identifiers of places already present in the trip.

    Events are matched within the trip; stays are orphaned (no day) when
    accepted, so they are matched by author instead. Returns a set of
    ``place_id`` values and a set of normalized names.
    """
    place_ids, names = set(), set()
    for pid, name in Event.objects.filter(trip=trip).values_list("place_id", "name"):
        if pid:
            place_ids.add(pid)
        names.add(name.strip().casefold())
    for pid, name in Stay.objects.filter(author=user).values_list("place_id", "name"):
        if pid:
            place_ids.add(pid)
        names.add(name.strip().casefold())
    return place_ids, names


def _is_already_added(grounded, place_ids, names) -> bool:
    if grounded.place_id and grounded.place_id in place_ids:
        return True
    return grounded.suggestion.name.strip().casefold() in names


def _build_visible_cards(trip, user, suggestions) -> list[dict]:
    """Turn grounded suggestions into cards, dropping ones already in the trip."""
    place_ids, names = _added_keys(trip, user)
    return [
        _to_card(s, _ACCEPT_URL)
        for s in suggestions
        if not _is_already_added(s, place_ids, names)
    ]


def _to_card(grounded, add_urls) -> dict:
    suggestion = grounded.suggestion
    kind = suggestion.kind.value
    icon, icon_color = _KIND_ICON[kind]
    return {
        "kind": kind,
        "name": suggestion.name,
        "description": suggestion.description,
        "icon": icon,
        "icon_color": icon_color,
        "address": grounded.address,
        "city": grounded.city,
        "lat": grounded.latitude,
        "lng": grounded.longitude,
        "place_id": grounded.place_id,
        "add_url": add_urls[kind],
    }


@login_required
def settings_view(request):
    """Render and save the per-user AI settings (BYOK key + preferences).

    Loaded into the profile page via HTMX and re-renders itself on save.
    """
    credentials = AICredentials.objects.filter(user=request.user).first()
    preferences, _ = SuggestionPreferences.objects.get_or_create(user=request.user)
    profile = get_profile(request.user)

    credentials_form = AICredentialsForm(request.POST or None, instance=credentials)
    preferences_form = SuggestionPreferencesForm(
        request.POST or None, instance=preferences
    )
    toggle_form = AISuggestionsToggleForm(request.POST or None, instance=profile)

    saved = False
    if request.method == "POST":
        if (
            toggle_form.is_valid()
            and credentials_form.is_valid()
            and preferences_form.is_valid()
        ):
            toggle_form.save()
            preferences_form.save()
            api_key = credentials_form.cleaned_data["api_key_encrypted"]
            if api_key:
                creds = credentials_form.save(commit=False)
                creds.user = request.user
                creds.save()
            saved = True

    return TemplateResponse(
        request,
        "suggestions/settings.html",
        {
            "credentials_form": credentials_form,
            "preferences_form": preferences_form,
            "toggle_form": toggle_form,
            "has_credentials": credentials is not None,
            "ai_enabled": profile.ai_suggestions_enabled,
            "saved": saved,
        },
    )


def _get_accessible_trip(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404
    return trip


@login_required
@require_POST
def generate(request, pk):
    """HTMX: generate AI suggestions for a trip and render them as cards.

    ``context`` selects the desktop map panel ("map") or the mobile modal
    ("modal"); ``refresh`` (Regenerate) bypasses the 24h cache.
    """
    trip = _get_accessible_trip(request, pk)
    is_modal = request.POST.get("context") == "modal"
    force_refresh = bool(request.POST.get("refresh"))
    stage = request.POST.get("stage_destination", "").strip() or None

    overrides = {}
    notes = request.POST.get("notes", "").strip()
    if notes:
        overrides["notes"] = notes
    kinds = request.POST.getlist("kinds")
    if kinds:
        overrides["kinds"] = kinds
    language = get_profile(request.user).language

    cards = []
    error_kind = None
    try:
        suggestions = generate_suggestions(
            request.user, trip, overrides, language, force_refresh, stage
        )
        # Filter out suggestions already added to the trip (e.g. served from the
        # cache after being accepted in a previous session) so they are not shown
        # again as fresh suggestions.
        cards = _build_visible_cards(trip, request.user, suggestions)
    except AISuggestionError as exc:
        error_kind = exc.kind

    return TemplateResponse(
        request,
        "suggestions/map-suggestions-results.html",
        {
            "trip": trip,
            "cards": cards,
            "error_kind": error_kind,
            "is_modal": is_modal,
            # A successful generation populated the cache, so the map button
            # becomes "Regenerate"; on error it stays "Generate".
            "has_cache": error_kind is None,
        },
    )


@login_required
@require_GET
def cached(request, pk):
    """HTMX: render the last cached suggestions without spending quota.

    Powers "show my last results" when the map AI tab is activated or the
    modal is reopened; falls back to a prompt inviting the user to generate.
    """
    trip = _get_accessible_trip(request, pk)
    suggestions = get_cached_suggestions(request.user, trip)
    cards = _build_visible_cards(trip, request.user, suggestions or [])
    return TemplateResponse(
        request,
        "suggestions/map-suggestions-results.html",
        {
            "trip": trip,
            "cards": cards,
            "error_kind": None,
            "is_modal": request.GET.get("context") == "modal",
            "from_cache": True,
            "awaiting_generation": suggestions is None,
            "has_cache": suggestions is not None,
        },
    )


@login_required
@require_GET
def suggestion_modal(request, pk):
    """HTMX: render the AI suggestions modal shell (mobile entry point).

    Pre-populates the results with the last cached suggestions (if any) so
    reopening the modal shows them without spending quota.
    """
    trip = _get_accessible_trip(request, pk)
    suggestions = get_cached_suggestions(request.user, trip)
    cards = _build_visible_cards(trip, request.user, suggestions or [])
    stages = get_trip_stages(trip)
    return TemplateResponse(
        request,
        "suggestions/suggestion-modal.html",
        {
            "trip": trip,
            "cards": cards,
            "has_cache": suggestions is not None,
            "stages": stages,
            "has_custom_stages": any(not s["is_main"] for s in stages),
        },
    )


def _accept(request, pk, kind):
    trip = _get_accessible_trip(request, pk)
    name = request.POST.get("name", "").strip()
    address = request.POST.get("address", "").strip()
    place_id = request.POST.get("google_place_id", "").strip()
    lat = request.POST.get("lat", "").strip()
    lng = request.POST.get("lng", "").strip()

    if name:
        if kind == "stay":
            obj = Stay(
                name=name, address=address or "", place_id=place_id, author=request.user
            )
        else:
            obj = build_categorized_event(
                _ACCEPT_CATEGORY[kind],
                trip=trip,
                name=name,
                address=address,
                place_id=place_id,
                last_modified_by=request.user,
            )
        if lat and lng:
            try:
                obj.latitude = float(lat)
                obj.longitude = float(lng)
            except ValueError:
                pass
        obj.save()

    context = {}
    # On the desktop map panel, refresh the events list out-of-band so the newly
    # added (orphaned) item shows immediately; the mobile modal has no panel and
    # relies on the unpairedModified trigger to reload the trip detail section.
    if request.POST.get("context") == "map":
        days_with_events, unassigned_events = _build_map_events_context(trip)
        context = {
            "trip": trip,
            "days_with_events": days_with_events,
            "unassigned_events": unassigned_events,
            "refresh_events_panel": True,
        }

    return TemplateResponse(
        request,
        "suggestions/suggestion-added.html",
        context,
        headers={"HX-Trigger": "unpairedModified"},
    )


@login_required
@require_POST
def accept_experience(request, pk):
    return _accept(request, pk, "experience")


@login_required
@require_POST
def accept_meal(request, pk):
    return _accept(request, pk, "meal")


@login_required
@require_POST
def accept_stay(request, pk):
    return _accept(request, pk, "stay")


@login_required
@require_POST
def dismiss_shared_key_notice(request, pk):
    """HTMX: permanently dismiss the shared-key notice for this trip and user."""
    trip = _get_accessible_trip(request, pk)
    SharedKeyNoticeDismissal.objects.get_or_create(user=request.user, trip=trip)
    return HttpResponse(status=204)


def _get_accessible_day(request, pk, day_id):
    trip = _get_accessible_trip(request, pk)
    day = get_object_or_404(Day, pk=day_id, trip=trip)
    return trip, day


def _to_stop_card(grounded) -> dict:
    """Turn a GroundedStop into the dict the day-itinerary preview renders."""
    stop = grounded.stop
    kind = stop.kind.value
    icon, icon_color = _KIND_ICON[kind]
    return {
        "kind": kind,
        "name": stop.name,
        "description": stop.description,
        "icon": icon,
        "icon_color": icon_color,
        "address": grounded.address,
        "city": grounded.city,
        "lat": grounded.latitude,
        "lng": grounded.longitude,
        "place_id": grounded.place_id,
        "duration_minutes": stop.estimated_duration_minutes,
        "existing_event_id": grounded.existing_event_id,
    }


@login_required
@require_GET
def plan_day_modal(request, pk, day_id):
    """HTMX: render the "plan this day" modal shell for a single day.

    When the day already holds events the modal offers the three strategies
    (add / unpair / delete); nothing is generated until the user submits.
    """
    trip, day = _get_accessible_day(request, pk, day_id)
    return TemplateResponse(
        request,
        "suggestions/plan-day-modal.html",
        {"trip": trip, "day": day, "has_events": day.events.exists()},
    )


@login_required
@require_POST
def generate_day(request, pk, day_id):
    """HTMX: generate a draft day itinerary and render it for review."""
    trip, day = _get_accessible_day(request, pk, day_id)
    strategy = request.POST.get("strategy", DAY_STRATEGY_ADD)
    if strategy not in DAY_STRATEGIES:
        strategy = DAY_STRATEGY_ADD
    force_refresh = bool(request.POST.get("refresh"))
    overrides = {}
    notes = request.POST.get("notes", "").strip()
    if notes:
        overrides["notes"] = notes
    language = get_profile(request.user).language

    stops = []
    error_kind = None
    try:
        grounded = generate_day_itinerary(
            request.user, trip, day, strategy, overrides, language, force_refresh
        )
        stops = [_to_stop_card(g) for g in grounded]
    except AISuggestionError as exc:
        error_kind = exc.kind

    return TemplateResponse(
        request,
        "suggestions/plan-day-results.html",
        {
            "trip": trip,
            "day": day,
            "stops": stops,
            "strategy": strategy,
            "error_kind": error_kind,
            "has_cache": error_kind is None,
        },
    )


def _create_day_event(user, trip, day, item, order) -> None:
    """Create an Experience/Meal on ``day`` from a submitted itinerary stop."""
    name = (item.get("name") or "").strip()
    category = _ACCEPT_CATEGORY.get(item.get("kind"))
    if not name or category is None:
        return
    obj = build_categorized_event(
        category,
        trip=trip,
        day=day,
        name=name,
        address=item.get("address") or "",
        city=item.get("city") or "",
        place_id=item.get("place_id") or "",
        order=order,
        last_modified_by=user,
    )
    lat, lng = item.get("lat"), item.get("lng")
    if lat is not None and lng is not None:
        try:
            obj.latitude = float(lat)
            obj.longitude = float(lng)
        except TypeError, ValueError:
            pass
    minutes = item.get("duration_minutes")
    if minutes:
        obj.estimated_duration = timedelta(minutes=int(minutes))
    obj.save()


def _apply_day_itinerary(user, trip, day, strategy, stops) -> None:
    """Apply an accepted day itinerary.

    ``unpair``/``delete`` detach or remove the day's current events first, then
    every accepted stop is created fresh. ``add`` reorders matched existing
    events in place, creates the new ones, and appends any existing event the
    user deselected after the accepted sequence.
    """
    existing = list(day.events.all())
    if strategy == DAY_STRATEGY_UNPAIR:
        Event.objects.filter(day=day).update(day=None)
    elif strategy == DAY_STRATEGY_DELETE:
        Event.objects.filter(day=day).delete()

    consumed = set()
    order = 0
    for item in stops:
        existing_id = item.get("existing_event_id")
        if existing_id and strategy == DAY_STRATEGY_ADD:
            Event.objects.filter(pk=existing_id, day=day).update(order=order)
            consumed.add(existing_id)
        else:
            _create_day_event(user, trip, day, item, order)
        order += 1

    if strategy == DAY_STRATEGY_ADD:
        for event in existing:
            if event.pk not in consumed:
                event.order = order
                event.save(update_fields=["order"])
                order += 1


@login_required
@require_POST
def accept_day(request, pk, day_id):
    """HTMX: apply an accepted day itinerary and refresh the day view."""
    trip, day = _get_accessible_day(request, pk, day_id)
    strategy = request.POST.get("strategy", DAY_STRATEGY_ADD)
    if strategy not in DAY_STRATEGIES:
        strategy = DAY_STRATEGY_ADD
    try:
        stops = json.loads(request.POST.get("stops", "[]"))
    except json.JSONDecodeError:
        stops = []

    _apply_day_itinerary(request.user, trip, day, strategy, stops)

    return TemplateResponse(
        request,
        "suggestions/day-applied.html",
        {"trip": trip, "day": day},
        headers={"HX-Trigger": f"dayModified{day.pk}, unpairedModified"},
    )


@login_required
@require_GET
def details(request, pk):
    """HTMX: fetch on-demand place details (website, phone, hours) for a card."""
    _get_accessible_trip(request, pk)

    place_id = request.GET.get("place_id", "").strip()
    place = None
    error = None
    if place_id:
        try:
            place = GooglePlacesClient().get_full_place_details(place_id)
        except GooglePlacesError as exc:
            error = str(exc)

    return TemplateResponse(
        request,
        "suggestions/suggestion-details.html",
        {"place": place, "error": error},
    )
