from datetime import date
from typing import Protocol, runtime_checkable

from suggestions.schemas import (
    DayItinerary,
    Suggestion,
    SuggestionPrefs,
    TripContext,
    TripItinerary,
    TripStage,
)


class AISuggestionError(Exception):
    """Raised when an AI provider fails to return usable suggestions.

    Mirrors trips.services.GooglePlacesError: callers catch this single type
    regardless of the underlying provider. ``kind`` classifies the failure so
    the UI can show an appropriate message: a configuration problem (missing or
    invalid key), a provider quota/rate limit, the app's own daily generation
    cap, or a generic error.
    """

    CONFIG = "config"
    QUOTA = "quota"
    RATE_LIMIT = "rate_limit"
    GENERIC = "generic"

    def __init__(self, message: str, kind: str = GENERIC):
        super().__init__(message)
        self.kind = kind


@runtime_checkable
class TripSuggestionProvider(Protocol):
    """Provider-agnostic contract. Each provider takes the user's API key and
    turns a trip context + preferences into validated suggestions."""

    def generate(
        self, context: TripContext, prefs: SuggestionPrefs
    ) -> list[Suggestion]: ...

    def generate_day(
        self,
        context: TripContext,
        prefs: SuggestionPrefs,
        day_date: date,
        day_stops: list[str] | None = None,
    ) -> DayItinerary: ...

    def generate_trip(
        self,
        context: TripContext,
        prefs: SuggestionPrefs,
        stages: list[TripStage],
    ) -> TripItinerary: ...
