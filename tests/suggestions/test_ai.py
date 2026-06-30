from unittest.mock import MagicMock, patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.ai.factory import get_provider
from suggestions.ai.gemini import GeminiProvider
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext

CONTEXT = TripContext(destination="Rome")
PREFS = SuggestionPrefs()


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

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_wraps_sdk_errors(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = RuntimeError("boom")

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError):
            provider.generate(CONTEXT, PREFS)

    @patch("suggestions.ai.gemini.genai.Client")
    def test_generate_raises_on_empty(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = MagicMock(parsed=None)

        provider = GeminiProvider("api-key")
        with pytest.raises(AISuggestionError):
            provider.generate(CONTEXT, PREFS)


class TestFactory:
    @patch("suggestions.ai.gemini.genai.Client")
    def test_get_provider_gemini(self, _mock_client_cls):
        provider = get_provider("gemini", "api-key")
        assert isinstance(provider, GeminiProvider)

    def test_get_provider_unknown(self):
        with pytest.raises(AISuggestionError):
            get_provider("unknown", "api-key")
