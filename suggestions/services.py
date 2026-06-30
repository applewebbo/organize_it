from dataclasses import dataclass

from suggestions.ai.base import AISuggestionError
from suggestions.ai.factory import get_provider
from suggestions.models import AICredentials, SuggestionPreferences
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext
from trips.models import Trip
from trips.services import GooglePlacesClient, GooglePlacesError

# Radius (meters) used to bias Google Places search around the destination.
_GROUNDING_RADIUS = 50000


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
        )

    for field in ("favored_experience_types", "dietary", "pace", "budget"):
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
) -> list[GroundedSuggestion]:
    """Full orchestration: provider call + validation + Google Places grounding.

    The API key is decrypted only here, immediately before the provider call.
    Suggestions that cannot be grounded are skipped.
    """
    credentials = AICredentials.objects.filter(user=user).first()
    if credentials is None or not credentials.api_key_encrypted:
        raise AISuggestionError("No AI credentials configured")

    provider = get_provider(credentials.provider, credentials.api_key_encrypted)
    context = build_trip_context(trip, language=language)
    preferences = merge_preferences(
        SuggestionPreferences.objects.filter(user=user).first(), overrides
    )

    suggestions = provider.generate(context, preferences)

    client = GooglePlacesClient()
    grounded = []
    for suggestion in suggestions:
        result = _ground(suggestion, context, client)
        if result is not None:
            grounded.append(result)
    return grounded
