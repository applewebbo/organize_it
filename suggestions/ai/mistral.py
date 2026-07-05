import logging

from mistralai.client import Mistral
from pydantic import BaseModel

from suggestions.ai.base import AISuggestionError
from suggestions.prompts import build_prompt
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "mistral-small-latest"


class SuggestionList(BaseModel):
    """Object-root wrapper for structured output.

    Mistral's ``json_schema`` response format requires an object at the schema
    root, so the bare ``list[Suggestion]`` used by Gemini is wrapped here.
    """

    suggestions: list[Suggestion]


def _error_kind(exc: Exception) -> str:
    """Classify an SDK/network error into an AISuggestionError kind."""
    # A valid API key is ASCII; a key with non-ASCII characters blows up while
    # encoding the auth header, before any request -> bad key = config.
    if isinstance(exc, UnicodeEncodeError):
        return AISuggestionError.CONFIG
    # mistralai SDK errors carry the raw httpx response with the HTTP status.
    status = getattr(getattr(exc, "raw_response", None), "status_code", None)
    if status == 429:
        return AISuggestionError.QUOTA
    if status in (400, 401, 403):
        return AISuggestionError.CONFIG
    return AISuggestionError.GENERIC


class MistralProvider:
    """Mistral AI implementation of TripSuggestionProvider.

    Uses the SDK's ``chat.parse`` structured output against the SuggestionList
    wrapper, so it returns already-parsed, validated Suggestion objects.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._client = Mistral(api_key=api_key)
        self._model = model

    def generate(
        self, context: TripContext, prefs: SuggestionPrefs
    ) -> list[Suggestion]:
        prompt = build_prompt(context, prefs)
        try:
            response = self._client.chat.parse(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format=SuggestionList,
            )
        except Exception as exc:  # SDK/network errors -> single error type
            kind = _error_kind(exc)
            # Log the raw provider error so the real cause is visible
            # server-side; the user only sees the vague, safe message.
            logger.warning("Mistral chat.parse failed (kind=%s): %s", kind, exc)
            raise AISuggestionError(str(exc), kind=kind) from exc

        parsed = response.choices[0].message.parsed if response.choices else None
        suggestions = parsed.suggestions if parsed else None
        if not suggestions:
            raise AISuggestionError("The AI provider returned no suggestions")
        return suggestions
