import hashlib
import json
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from django.core.cache import cache

from suggestions.ai.base import AISuggestionError
from suggestions.ai.factory import get_provider
from suggestions.models import AICredentials, SuggestionPreferences
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext
from trips.models import Trip
from trips.services import GooglePlacesClient, GooglePlacesError

# Radius (meters) used to bias Google Places search around the destination.
_GROUNDING_RADIUS = 50000

# Generated suggestions are cached for a day to spare the free-tier quota.
_CACHE_TTL = 24 * 3600


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


def build_trip_context(trip: Trip, language: str = "en") -> TripContext:
    """Build the TripContext fed to the provider from a Trip."""
    return TripContext(
        destination=trip.destination,
        latitude=trip.destination_latitude,
        longitude=trip.destination_longitude,
        start_date=trip.start_date,
        end_date=trip.end_date,
        language=language,
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
            pace=defaults.pace,
            budget=defaults.budget,
            notes=defaults.notes,
            result_count=defaults.result_count,
        )

    for field in ("favored_experience_types", "dietary", "pace", "budget", "kinds"):
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
) -> GroundedSuggestion | None:
    """Resolve a suggestion to a real place; return None if not found."""
    query = " ".join(
        part
        for part in (suggestion.name, suggestion.address or suggestion.city)
        if part
    )
    location_bias = None
    if context.latitude is not None and context.longitude is not None:
        location_bias = (context.latitude, context.longitude, _GROUNDING_RADIUS)

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
    # grounded places that fall outside the bias radius so results stay scoped to
    # the destination / selected stage.
    if location_bias is not None:
        lat0, lng0, radius = location_bias
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
    credentials = AICredentials.objects.filter(user=user).first()
    if credentials is None or not credentials.api_key_encrypted:
        raise AISuggestionError(
            "No AI credentials configured", kind=AISuggestionError.CONFIG
        )

    context = build_trip_context(trip, language=language)
    if stage:
        _apply_stage(context, trip, stage)
    preferences = merge_preferences(
        SuggestionPreferences.objects.filter(user=user).first(), overrides
    )

    key = _cache_key(trip, preferences, language, stage)
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached

    provider = get_provider(credentials.provider, credentials.api_key_encrypted)
    suggestions = provider.generate(context, preferences)

    # Drop kinds the user did not ask for before grounding, so discarded kinds
    # do not consume the result_count budget or trigger Google Places calls.
    if preferences.kinds:
        suggestions = [s for s in suggestions if s.kind.value in preferences.kinds]

    client = GooglePlacesClient()
    grounded = []
    # Cap the number we try to ground so a verbose model response cannot trigger
    # an unbounded number of Google Places calls.
    for suggestion in suggestions[: preferences.result_count]:
        result = _ground(suggestion, context, client)
        if result is not None:
            grounded.append(result)

    cache.set(key, grounded, _CACHE_TTL)
    return grounded


def get_cached_suggestions(
    user,
    trip: Trip,
    overrides: dict | None = None,
    language: str = "en",
    stage: str | None = None,
) -> list[GroundedSuggestion] | None:
    """Return cached suggestions for this trip + preferences, or None.

    Peeks the cache without ever calling the AI provider, so it spends no
    quota. Used to re-show the last generated results when the panel/modal is
    reopened.
    """
    preferences = merge_preferences(
        SuggestionPreferences.objects.filter(user=user).first(), overrides
    )
    key = _cache_key(trip, preferences, language, stage)
    return cache.get(key)
