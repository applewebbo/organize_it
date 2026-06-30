import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import connection

from suggestions.models import AICredentials, SuggestionPreferences
from tests.suggestions.factories import (
    AICredentialsFactory,
    SuggestionPreferencesFactory,
)

pytestmark = pytest.mark.django_db


class TestAICredentials:
    def test_str_does_not_expose_key(self):
        creds = AICredentialsFactory(api_key_encrypted="super-secret")
        result = str(creds)
        assert "super-secret" not in result
        assert creds.user.email in result

    def test_default_provider_is_gemini(self):
        creds = AICredentialsFactory()
        assert creds.provider == AICredentials.Provider.GEMINI

    def test_api_key_round_trip(self):
        creds = AICredentialsFactory(api_key_encrypted="my-plain-key")
        creds.refresh_from_db()
        assert creds.api_key_encrypted == "my-plain-key"

    def test_api_key_is_encrypted_at_rest(self):
        creds = AICredentialsFactory(api_key_encrypted="my-plain-key")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT api_key_encrypted FROM suggestions_aicredentials WHERE id = %s",
                [creds.id],
            )
            raw = cursor.fetchone()[0]
        assert raw != "my-plain-key"
        fernet = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
        assert fernet.decrypt(raw.encode()).decode() == "my-plain-key"

    def test_one_to_one_with_user(self):
        creds = AICredentialsFactory()
        assert creds.user.ai_credentials == creds


class TestSuggestionPreferences:
    def test_str(self):
        prefs = SuggestionPreferencesFactory()
        assert prefs.user.email in str(prefs)

    def test_defaults(self):
        prefs = SuggestionPreferencesFactory()
        assert prefs.favored_experience_types == []
        assert prefs.dietary == SuggestionPreferences.Dietary.NONE
        assert prefs.pace == SuggestionPreferences.Pace.MODERATE
        assert prefs.budget == SuggestionPreferences.Budget.MEDIUM
        assert prefs.notes == ""

    def test_one_to_one_with_user(self):
        prefs = SuggestionPreferencesFactory()
        assert prefs.user.suggestion_preferences == prefs

    def test_favored_experience_types_persists(self):
        prefs = SuggestionPreferencesFactory(favored_experience_types=[1, 3])
        prefs.refresh_from_db()
        assert prefs.favored_experience_types == [1, 3]
