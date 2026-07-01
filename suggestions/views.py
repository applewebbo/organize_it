from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import get_profile
from suggestions.ai.base import AISuggestionError
from suggestions.forms import AICredentialsForm, SuggestionPreferencesForm
from suggestions.models import AICredentials, SuggestionPreferences
from suggestions.services import generate_suggestions
from trips.models import Event, Stay, Trip
from trips.services import GooglePlacesClient, GooglePlacesError
from trips.utils import accessible_trips_qs
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

    credentials_form = AICredentialsForm(request.POST or None, instance=credentials)
    preferences_form = SuggestionPreferencesForm(
        request.POST or None, instance=preferences
    )

    saved = False
    if request.method == "POST":
        if credentials_form.is_valid() and preferences_form.is_valid():
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
            "has_credentials": credentials is not None,
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

    overrides = {}
    notes = request.POST.get("notes", "").strip()
    if notes:
        overrides["notes"] = notes
    language = get_profile(request.user).language

    cards = []
    error_kind = None
    try:
        suggestions = generate_suggestions(
            request.user, trip, overrides, language, force_refresh
        )
        # Filter out suggestions already added to the trip (e.g. served from the
        # cache after being accepted in a previous session) so they are not shown
        # again as fresh suggestions.
        place_ids, names = _added_keys(trip, request.user)
        cards = [
            _to_card(s, _ACCEPT_URL)
            for s in suggestions
            if not _is_already_added(s, place_ids, names)
        ]
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
        },
    )


@login_required
@require_GET
def suggestion_modal(request, pk):
    """HTMX: render the AI suggestions modal shell (mobile entry point)."""
    trip = _get_accessible_trip(request, pk)
    return TemplateResponse(
        request, "suggestions/suggestion-modal.html", {"trip": trip}
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
            obj = Event(
                trip=trip,
                name=name,
                address=address,
                place_id=place_id,
                category=_ACCEPT_CATEGORY[kind],
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
