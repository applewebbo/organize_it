from unittest.mock import MagicMock, patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.ai.factory import get_provider
from suggestions.ai.gemini import GeminiProvider
from suggestions.ai.mistral import MistralProvider, SuggestionList
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext

CONTEXT = TripContext(destination="Rome")
PREFS = SuggestionPrefs()


class _ApiError(Exception):
    """Mimics a google-genai APIError carrying an HTTP status code."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class _SdkError(Exception):
    """Mimics a mistralai SDKError carrying an httpx response with a status."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.raw_response = MagicMock(status_code=status_code)


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


def _mistral_response(suggestions):
    """Build a mock chat.parse response with the given parsed suggestions."""
    message = MagicMock()
    message.parsed = (
        SuggestionList(suggestions=suggestions) if suggestions is not None else None
    )
    choice = MagicMock(message=message)
    return MagicMock(choices=[choice])


class TestMistralProvider:
    @patch("suggestions.ai.mistral.Mistral")
    def test_generate_success(self, mock_client_cls):
        suggestion = Suggestion(kind="meal", name="Trattoria", type=3)
        mock_client = mock_client_cls.return_value
        mock_client.chat.parse.return_value = _mistral_response([suggestion])

        provider = MistralProvider("api-key")
        result = provider.generate(CONTEXT, PREFS)

        assert result == [suggestion]
        mock_client_cls.assert_called_once_with(api_key="api-key")
        # structured output is requested against the object-root wrapper
        kwargs = mock_client.chat.parse.call_args.kwargs
        assert kwargs["response_format"] is SuggestionList

    @patch("suggestions.ai.mistral.Mistral")
    def test_generate_wraps_sdk_errors(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.chat.parse.side_effect = RuntimeError("boom")

        provider = MistralProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.GENERIC

    @patch("suggestions.ai.mistral.Mistral")
    def test_generate_classifies_quota_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.chat.parse.side_effect = _SdkError("rate limited", status_code=429)

        provider = MistralProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.QUOTA

    @patch("suggestions.ai.mistral.Mistral")
    def test_generate_classifies_config_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.chat.parse.side_effect = _SdkError("unauthorized", status_code=401)

        provider = MistralProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.CONFIG

    @patch("suggestions.ai.mistral.Mistral")
    def test_generate_classifies_non_ascii_key_as_config(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.chat.parse.side_effect = UnicodeEncodeError(
            "ascii", "ò", 0, 1, "ordinal not in range(128)"
        )

        provider = MistralProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.CONFIG

    @patch("suggestions.ai.mistral.Mistral")
    def test_generate_raises_on_empty(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.chat.parse.return_value = _mistral_response(None)

        provider = MistralProvider("api-key")
        with pytest.raises(AISuggestionError) as exc_info:
            provider.generate(CONTEXT, PREFS)
        assert exc_info.value.kind == AISuggestionError.GENERIC


class TestFactory:
    @patch("suggestions.ai.gemini.genai.Client")
    def test_get_provider_gemini(self, _mock_client_cls):
        provider = get_provider("gemini", "api-key")
        assert isinstance(provider, GeminiProvider)

    @patch("suggestions.ai.mistral.Mistral")
    def test_get_provider_mistral(self, _mock_client_cls):
        provider = get_provider("mistral", "api-key")
        assert isinstance(provider, MistralProvider)

    def test_get_provider_unknown(self):
        with pytest.raises(AISuggestionError):
            get_provider("unknown", "api-key")
