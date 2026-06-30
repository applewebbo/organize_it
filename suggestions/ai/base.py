from typing import Protocol, runtime_checkable

from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext


class AISuggestionError(Exception):
    """Raised when an AI provider fails to return usable suggestions.

    Mirrors trips.services.GooglePlacesError: callers catch this single type
    regardless of the underlying provider.
    """


@runtime_checkable
class TripSuggestionProvider(Protocol):
    """Provider-agnostic contract. Each provider takes the user's API key and
    turns a trip context + preferences into validated suggestions."""

    def generate(
        self, context: TripContext, prefs: SuggestionPrefs
    ) -> list[Suggestion]: ...
