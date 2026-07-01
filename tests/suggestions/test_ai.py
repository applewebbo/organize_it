from unittest.mock import MagicMock, patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.ai.factory import get_provider
from suggestions.ai.gemini import GeminiProvider
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext

CONTEXT = TripContext(destination="Rome")
PREFS = SuggestionPrefs()


class _ApiError(Exception):
    """Mimics a google-genai APIError carrying an HTTP status code."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class TestGeminiProvider:
    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_success(self, mock_client_cls):
        suggestion = Suggestion(kind="meal", name="Trattoria", type=3)
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = MagicMock(
            parsed=[suggestion]
        )

        provider = GeminiProvider("api-key")
        result = provider.generate(CONTEXT, PREFS)

        assert result == [suggestion]
        mock_client_cls.assert_called_once_with(api_key="api-key")
        # thinking disabled so structured output is not starved of tokens
        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.thinking_config.thinking_budget == 0

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_wraps_sdk_errors(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = RuntimeError("boom")

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.GENERIC

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_classifies_quota_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = _ApiError(
            "429 RESOURCE_EXHAUSTED", code=429
        )

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.QUOTA

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_classifies_config_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = _ApiError(
            "API_KEY_INVALID", code=400
        )

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.CONFIG

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_classifies_non_ascii_key_as_config(self, mock_client_cls):
        # A key with accented characters fails while encoding the auth header.
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = UnicodeEncodeError(
            "ascii", "ò", 0, 1, "ordinal not in range(128)"
        )

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.CONFIG

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_raises_on_empty(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = MagicMock(parsed=None)

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.GENERIC


class TestFactory:
    @patch("suggestions.ai.gemini.genai.Client")
    def test_get_provider_gemini(self, _mock_client_cls):
        provider = get_provider("gemini", "api-key")
        assert isinstance(provider, GeminiProvider)

    def test_get_provider_unknown(self):
        with pytest.raises(AISuggestionError):
            get_provider("unknown", "api-key")
