import hashlib
import json
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from django.core.cache import cache

from suggestions.ai.base import AISuggestionError
from suggestions.ai.factory import get_provider
from suggestions.models import (
    AICredentials,
    SharedKeyNoticeDismissal,
    SuggestionPreferences,
)
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext
from trips.models import Event, Stay, Trip
from trips.services import GooglePlacesClient, GooglePlacesError

# Radius (meters) used to bias Google Places search around the destination.
_GROUNDING_RADIUS = 50000

# Google Places rejects a locationBias circle radius above 50km. Wider search
# areas (e.g. day trips) are still enforced via the post-grounding distance
# check, so only the soft bias hint sent to Google is clamped to this cap.
_MAX_BIAS_RADIUS = 50000

# Per-preference search radius in meters. Maps the user-facing SearchRadius
# choice to the Google Places location-bias radius; "nearby" keeps the historic
# default so existing cached results stay valid.
_RADIUS_METERS = {
    "city": 8000,
    "nearby": _GROUNDING_RADIUS,
    "day_trips": 150000,
}

# Generated suggestions are cached for a day to spare the free-tier quota.
_CACHE_TTL = 24 * 3600

# The "last results" pointer lives longer than the prefs cache so reopening the
# panel/modal the next day still re-shows the last generation without spending
# quota. It is pure UX convenience, so a longer TTL has no quota downside.
_LAST_TTL = 48 * 3600

# Ask the model for more candidates than requested so that grounding rejections
# (place not found, outside the bias radius) still leave enough to reach the
# user's target count. Grounding stops as soon as the target is met, so the
# extra candidates cost nothing when grounding succeeds cleanly.
_OVERFETCH_FACTOR = 3


def _cache_key(
    trip: Trip,
    preferences: SuggestionPrefs,
    language: str,
    stage: str | None = None,
) -> str:
    payload = json.dumps(
        {
            "trip": trip.pk,
            "lang": language,
            "prefs": preferences.model_dump(),
            "stage": stage,
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"ai_sugg:{trip.pk}:{digest}"


def _last_key(user, trip: Trip) -> str:
    """Key for the most recent generation, independent of the prefs/stage used.

    Reopening the panel or modal cannot reconstruct the exact prefs-based key
    (kinds, notes, stage are chosen at generation time), so the latest results
    are also stored under this stable pointer for the "show my last results"
    peek.
    """
    return f"ai_sugg_last:{trip.pk}:{user.pk}"


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres between two lat/lng points."""
    r = 6371000
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _apply_stage(context: TripContext, trip: Trip, stage: str) -> None:
    """Scope the context to a single stage: use its name as the destination and
    centre the location bias on the stage's days."""
    context.destination = stage
    coords = list(
        trip.days.filter(destination=stage)
        .exclude(destination_latitude=None)
        .values_list("destination_latitude", "destination_longitude")
    )
    if coords:
        context.latitude = sum(c[0] for c in coords) / len(coords)
        context.longitude = sum(c[1] for c in coords) / len(coords)
    else:
        context.latitude = None
        context.longitude = None


@dataclass
class GroundedSuggestion:
    """A validated suggestion enriched with real location data from Google
    Places, ready to be turned into an Experience / Meal / Stay."""

    suggestion: Suggestion
    address: str
    city: str
    latitude: float
    longitude: float
    place_id: str


def _place_label(name: str, city: str) -> str:
    return f"{name} ({city})" if city else name


def _existing_places(trip: Trip, stage: str | None) -> list[str]:
    """Names of already-planned events + stays, scoped to a stage when given."""
    if stage:
        events = Event.objects.filter(trip=trip, day__destination=stage)
        stays = Stay.objects.filter(days__trip=trip, days__destination=stage)
    else:
        events = trip.all_events.all()
        stays = Stay.objects.filter(days__trip=trip)
    labels = [_place_label(e.name, e.city) for e in events]
    labels += [_place_label(s.name, s.city) for s in stays.distinct()]
    return labels


def _weather_lines(trip: Trip, stage: str | None) -> list[str]:
    """Compact per-day weather summaries, scoped to a stage when given."""
    days = trip.days.filter(weather_data__isnull=False)
    if stage:
        days = days.filter(destination=stage)
    lines = []
    for day in days.order_by("number"):
        w = day.weather_data
        lines.append(
            f"{day.date}: {w['weather_label']}, "
            f"{round(w['temperature_min'])}–{round(w['temperature_max'])}°C, "
            f"{w['precipitation_sum']}mm rain"
        )
    return lines


def build_trip_context(
    trip: Trip, language: str = "en", stage: str | None = None
) -> TripContext:
    """Build the TripContext fed to the provider from a Trip.

    ``existing_places`` and ``weather`` are scoped to ``stage`` when one is
    selected, so per-stage generations only see that stage's planned places and
    forecast.
    """
    return TripContext(
        destination=trip.destination,
        latitude=trip.destination_latitude,
        longitude=trip.destination_longitude,
        start_date=trip.start_date,
        end_date=trip.end_date,
        language=language,
        existing_places=_existing_places(trip, stage),
        weather=_weather_lines(trip, stage),
    )


def merge_preferences(
    defaults: SuggestionPreferences | None, overrides: dict | None = None
) -> SuggestionPrefs:
    """Merge persistent user defaults with ephemeral per-trip overrides.

    Per-trip values override the defaults field by field; free-text notes are
    concatenated rather than replaced.
    """
    overrides = overrides or {}
    merged = SuggestionPrefs()
    if defaults is not None:
        merged = SuggestionPrefs(
            favored_experience_types=defaults.favored_experience_types,
            dietary=defaults.dietary,
            budget=defaults.budget,
            travel_party=defaults.travel_party,
            travel_style=defaults.travel_style,
            interests=defaults.interests,
            cuisine=defaults.cuisine,
            search_radius=defaults.search_radius,
            notes=defaults.notes,
            result_count=defaults.result_count,
        )

    for field in ("favored_experience_types", "dietary", "budget", "kinds"):
        if overrides.get(field) is not None:
            setattr(merged, field, overrides[field])

    extra_notes = overrides.get("notes")
    if extra_notes:
        merged.notes = f"{merged.notes}\n{extra_notes}".strip()

    return merged


def _ground(
    suggestion: Suggestion,
    context: TripContext,
    client: GooglePlacesClient,
    radius: int = _GROUNDING_RADIUS,
) -> GroundedSuggestion | None:
    """Resolve a suggestion to a real place; return None if not found."""
    query = " ".join(
        part
        for part in (suggestion.name, suggestion.address or suggestion.city)
        if part
    )
    location_bias = None
    if context.latitude is not None and context.longitude is not None:
        location_bias = (
            context.latitude,
            context.longitude,
            min(radius, _MAX_BIAS_RADIUS),
        )

    try:
        results = client.search_text(
            query,
            max_results=1,
            location_bias=location_bias,
            language_code=context.language,
        )
    except GooglePlacesError:
        return None

    if not results:
        return None

    place = results[0]
    # locationBias is a soft hint: Google may still return a stronger text match
    # in another city (e.g. a same-named restaurant hundreds of km away). Reject
    # grounded places that fall outside the requested radius so results stay
    # scoped to the destination / selected stage. The acceptance radius is the
    # full requested value, which may exceed the clamped bias hint (day trips).
    if location_bias is not None:
        lat0, lng0, _bias = location_bias
        if _haversine_m(lat0, lng0, place.lat, place.lng) > radius:
            return None

    return GroundedSuggestion(
        suggestion=suggestion,
        address=place.address,
        city=suggestion.city,
        latitude=place.lat,
        longitude=place.lng,
        place_id=place.place_id,
    )


def resolve_credentials(user, trip: Trip) -> AICredentials | None:
    """Return the credentials to use for ``user`` generating on ``trip``.

    The user's own key always takes precedence. When they have none, fall back
    to the trip author's key, but only if the author opted in to sharing it with
    collaborators. Returns None when no usable key is available.
    """
    own = AICredentials.objects.filter(user=user).first()
    if own is not None and own.api_key_encrypted:
        return own

    if trip.author_id != user.pk:
        shared = AICredentials.objects.filter(
            user=trip.author, share_with_collaborators=True
        ).first()
        if shared is not None and shared.api_key_encrypted:
            return shared

    return None


def should_show_shared_key_notice(user, trip: Trip) -> bool:
    """Whether to show the shared-key notice to ``user`` on ``trip``.

    Shown only to collaborators (not the author) when the trip author shares a
    key and the user has not dismissed the notice for this trip yet.
    """
    if trip.author_id == user.pk:
        return False
    shared = AICredentials.objects.filter(
        user=trip.author, share_with_collaborators=True
    ).first()
    if shared is None or not shared.api_key_encrypted:
        return False
    return not SharedKeyNoticeDismissal.objects.filter(user=user, trip=trip).exists()


def generate_suggestions(
    user,
    trip: Trip,
    overrides: dict | None = None,
    language: str = "en",
    force_refresh: bool = False,
    stage: str | None = None,
) -> list[GroundedSuggestion]:
    """Full orchestration: provider call + validation + Google Places grounding.

    Results are cached per trip + preferences for a day so reopening the modal
    or pressing "Generate" again does not spend quota; ``force_refresh`` (the
    "Regenerate" button) bypasses the cache. The API key is decrypted only
    here, immediately before the provider call. Ungrounded suggestions are
    skipped.
    """
    credentials = resolve_credentials(user, trip)
    if credentials is None:
        raise AISuggestionError(
            "No AI credentials configured", kind=AISuggestionError.CONFIG
        )

    context = build_trip_context(trip, language=language, stage=stage)
    if stage:
        _apply_stage(context, trip, stage)
    preferences = merge_preferences(
        SuggestionPreferences.objects.filter(user=user).first(), overrides
    )

    key = _cache_key(trip, preferences, language, stage)
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            cache.set(_last_key(user, trip), cached, _LAST_TTL)
            return cached

    provider = get_provider(credentials.provider, credentials.api_key_encrypted)
    # Over-request so grounding rejections still leave enough to hit the target.
    fetch_prefs = preferences.model_copy(
        update={"result_count": preferences.result_count * _OVERFETCH_FACTOR}
    )
    suggestions = provider.generate(context, fetch_prefs)

    # Drop kinds the user did not ask for before grounding, so discarded kinds
    # do not consume the result_count budget or trigger Google Places calls.
    if preferences.kinds:
        suggestions = [s for s in suggestions if s.kind.value in preferences.kinds]

    client = GooglePlacesClient()
    radius = _RADIUS_METERS.get(preferences.search_radius, _GROUNDING_RADIUS)
    grounded = []
    # Ground candidates until we reach the requested count; stopping early keeps
    # Google Places calls bounded when grounding succeeds cleanly.
    for suggestion in suggestions:
        if len(grounded) >= preferences.result_count:
            break
        result = _ground(suggestion, context, client, radius)
        if result is not None:
            grounded.append(result)

    cache.set(key, grounded, _CACHE_TTL)
    cache.set(_last_key(user, trip), grounded, _LAST_TTL)
    return grounded


def get_cached_suggestions(user, trip: Trip) -> list[GroundedSuggestion] | None:
    """Return the most recently generated suggestions for this trip, or None.

    Peeks the cache without ever calling the AI provider, so it spends no
    quota. Used to re-show the last generated results when the panel/modal is
    reopened, regardless of the prefs/stage that produced them.
    """
    return cache.get(_last_key(user, trip))
