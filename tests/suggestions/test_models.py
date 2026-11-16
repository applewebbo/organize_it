import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import connection

from suggestions.models import AICredentials, DayPlanStop, SuggestionPreferences
from tests.suggestions.factories import (
    AICredentialsFactory,
    DayPlanStopFactory,
    SharedKeyNoticeDismissalFactory,
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

    def test_share_with_collaborators_defaults_off(self):
        creds = AICredentialsFactory()
        assert creds.share_with_collaborators is False


class TestSharedKeyNoticeDismissal:
    def test_str(self):
        dismissal = SharedKeyNoticeDismissalFactory()
        result = str(dismissal)
        assert dismissal.user.email in result
        assert str(dismissal.trip_id) in result

    def test_unique_per_user_and_trip(self):
        from django.db import IntegrityError

        dismissal = SharedKeyNoticeDismissalFactory()
        with pytest.raises(IntegrityError):
            SharedKeyNoticeDismissalFactory(user=dismissal.user, trip=dismissal.trip)


class TestSuggestionPreferences:
    def test_str(self):
        prefs = SuggestionPreferencesFactory()
        assert prefs.user.email in str(prefs)

    def test_defaults(self):
        prefs = SuggestionPreferencesFactory()
        assert prefs.favored_experience_types == []
        assert prefs.dietary == SuggestionPreferences.Dietary.NONE
        assert prefs.budget == SuggestionPreferences.Budget.MEDIUM
        assert prefs.travel_party == SuggestionPreferences.TravelParty.UNSPECIFIED
        assert prefs.travel_style == SuggestionPreferences.TravelStyle.BALANCED
        assert prefs.cuisine == SuggestionPreferences.Cuisine.ANY
        assert prefs.interests == []
        assert prefs.search_radius == SuggestionPreferences.SearchRadius.NEARBY
        assert prefs.notes == ""

    def test_interests_persists(self):
        prefs = SuggestionPreferencesFactory(interests=["history", "art"])
        prefs.refresh_from_db()
        assert prefs.interests == ["history", "art"]

    def test_one_to_one_with_user(self):
        prefs = SuggestionPreferencesFactory()
        assert prefs.user.suggestion_preferences == prefs

    def test_favored_experience_types_persists(self):
        prefs = SuggestionPreferencesFactory(favored_experience_types=[1, 3])
        prefs.refresh_from_db()
        assert prefs.favored_experience_types == [1, 3]


class TestDayPlanStop:
    def test_str(self):
        stop = DayPlanStopFactory(name="Museo Egizio")
        assert "Museo Egizio" in str(stop)

    def test_ordered_by_order_field(self):
        from tests.trips.factories import TripFactory

        trip = TripFactory()
        day = trip.days.first()
        second = DayPlanStopFactory(day=day, order=1)
        first = DayPlanStopFactory(day=day, order=0)
        assert list(DayPlanStop.objects.filter(day=day)) == [first, second]

    def test_existing_event_set_null_on_delete(self):
        from tests.trips.factories import ExperienceFactory

        event = ExperienceFactory()
        stop = DayPlanStopFactory(day=event.day, existing_event=event)
        event.delete()
        stop.refresh_from_db()
        assert stop.existing_event is None

    def test_deleted_with_day(self):
        from tests.trips.factories import TripFactory

        trip = TripFactory()
        day = trip.days.first()
        DayPlanStopFactory(day=day)
        day.delete()
        assert DayPlanStop.objects.count() == 0
