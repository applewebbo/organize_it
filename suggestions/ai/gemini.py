from google import genai
from google.genai import types

from suggestions.ai.base import AISuggestionError
from suggestions.prompts import build_prompt
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext

DEFAULT_MODEL = "gemini-3.1-flash-lite"


def _error_kind(exc: Exception) -> str:
    """Classify an SDK/network error into an AISuggestionError kind."""
    code = getattr(exc, "code", None)
    text = str(exc)
    if code == 429 or "RESOURCE_EXHAUSTED" in text:
        return AISuggestionError.QUOTA
    if (
        code in (400, 401, 403)
        or "API_KEY_INVALID" in text
        or "API key not valid" in text
        or "PERMISSION_DENIED" in text
    ):
        return AISuggestionError.CONFIG
    return AISuggestionError.GENERIC


class GeminiProvider:
    """Google Gemini implementation of TripSuggestionProvider.

    Uses the Pydantic Suggestion schema as the structured-output schema, so the
    SDK returns already-parsed, validated Suggestion objects.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(
        self, context: TripContext, prefs: SuggestionPrefs
    ) -> list[Suggestion]:
        prompt = build_prompt(context, prefs)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[Suggestion],
                    # Disable "thinking" (default-on for 2.5 models): with
                    # structured output it can consume the whole output budget
                    # and return an empty/truncated response.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except Exception as exc:  # SDK/network errors -> single error type
            raise AISuggestionError(str(exc), kind=_error_kind(exc)) from exc

        suggestions = response.parsed
        if not suggestions:
            raise AISuggestionError("The AI provider returned no suggestions")
        return suggestions
