import pytest

from accounts.models import Profile
from suggestions.models import AICredentials, SuggestionPreferences
from tests.suggestions.factories import AICredentialsFactory
from tests.test import TestCase

pytestmark = pytest.mark.django_db

BASE_DATA = {
    "provider": "gemini",
    "dietary": "none",
    "budget": "medium",
    "travel_party": "unspecified",
    "travel_style": "balanced",
    "cuisine": "any",
    "search_radius": "nearby",
    "result_count": 8,
}


class TestSuggestionSettingsView(TestCase):
    def test_unauthenticated_get(self):
        self.get("suggestions:settings")
        self.response_302()

    def test_get_renders_and_creates_preferences(self):
        user = self.make_user("user")
        with self.login(user):
            response = self.get("suggestions:settings")
        self.response_200(response)
        assert "suggestions/settings.html" in [t.name for t in response.templates]
        assert SuggestionPreferences.objects.filter(user=user).exists()
        assert response.context["has_credentials"] is False

    def test_get_with_existing_credentials(self):
        user = self.make_user("user")
        AICredentialsFactory(user=user)
        with self.login(user):
            response = self.get("suggestions:settings")
        self.response_200(response)
        assert response.context["has_credentials"] is True
        assert "A key is already configured." in response.content.decode()

    def test_post_creates_credentials_with_key(self):
        user = self.make_user("user")
        data = {**BASE_DATA, "api_key_encrypted": "fresh-key"}
        with self.login(user):
            response = self.post("suggestions:settings", data=data)
        self.response_200(response)
        assert response.context["saved"] is True
        creds = AICredentials.objects.get(user=user)
        assert creds.api_key_encrypted == "fresh-key"

    def test_post_without_key_saves_preferences_only(self):
        user = self.make_user("user")
        data = {**BASE_DATA, "notes": "kids", "api_key_encrypted": ""}
        with self.login(user):
            response = self.post("suggestions:settings", data=data)
        self.response_200(response)
        assert response.context["saved"] is True
        assert not AICredentials.objects.filter(user=user).exists()
        assert SuggestionPreferences.objects.get(user=user).notes == "kids"

    def test_post_blank_key_keeps_existing(self):
        user = self.make_user("user")
        AICredentialsFactory(user=user, api_key_encrypted="kept-key")
        data = {**BASE_DATA, "api_key_encrypted": ""}
        with self.login(user):
            response = self.post("suggestions:settings", data=data)
        self.response_200(response)
        assert AICredentials.objects.get(user=user).api_key_encrypted == "kept-key"

    def test_post_updates_existing_key(self):
        user = self.make_user("user")
        AICredentialsFactory(user=user, api_key_encrypted="old-key")
        data = {**BASE_DATA, "api_key_encrypted": "new-key"}
        with self.login(user):
            self.post("suggestions:settings", data=data)
        assert AICredentials.objects.get(user=user).api_key_encrypted == "new-key"

    def test_post_saves_favored_experience_types(self):
        user = self.make_user("user")
        data = {**BASE_DATA, "favored_experience_types": ["1", "3"]}
        with self.login(user):
            self.post("suggestions:settings", data=data)
        assert SuggestionPreferences.objects.get(
            user=user
        ).favored_experience_types == [1, 3]

    def test_post_invalid_does_not_save(self):
        user = self.make_user("user")
        data = {**BASE_DATA, "dietary": "invalid-choice"}
        with self.login(user):
            response = self.post("suggestions:settings", data=data)
        self.response_200(response)
        assert response.context["saved"] is False

    def test_ai_disabled_by_default(self):
        user = self.make_user("user")
        with self.login(user):
            response = self.get("suggestions:settings")
        assert response.context["ai_enabled"] is False

    def test_post_enables_ai_suggestions(self):
        user = self.make_user("user")
        data = {**BASE_DATA, "ai_suggestions_enabled": "on"}
        with self.login(user):
            response = self.post("suggestions:settings", data=data)
        self.response_200(response)
        assert response.context["ai_enabled"] is True
        assert Profile.objects.get(user=user).ai_suggestions_enabled is True

    def test_post_disables_ai_suggestions(self):
        user = self.make_user("user")
        Profile.objects.filter(user=user).update(ai_suggestions_enabled=True)
        # Unchecked checkbox is absent from the POST payload → disabled
        with self.login(user):
            self.post("suggestions:settings", data=BASE_DATA)
        assert Profile.objects.get(user=user).ai_suggestions_enabled is False
