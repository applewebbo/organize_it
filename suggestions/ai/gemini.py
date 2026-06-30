from google import genai
from google.genai import types

from suggestions.ai.base import AISuggestionError
from suggestions.prompts import build_prompt
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext

DEFAULT_MODEL = "gemini-2.0-flash"


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
                ),
            )
        except Exception as exc:  # SDK/network errors -> single error type
            raise AISuggestionError(str(exc)) from exc

        suggestions = response.parsed
        if not suggestions:
            raise AISuggestionError("The AI provider returned no suggestions")
        return suggestions
