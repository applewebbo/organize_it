from datetime import timedelta

import pytest
from django.utils import timezone

from suggestions.services import has_own_ai_key
from tests.suggestions.factories import AICredentialsFactory
from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import Trip
from trips.tasks import cleanup_abandoned_wizard_trips
from trips.utils.queries import get_trips

pytestmark = pytest.mark.django_db


class TestWizardModelFields(TestCase):
    def test_quick_created_trip_is_completed_by_default(self):
        trip = TripFactory()
        assert trip.wizard_completed is True
        assert trip.wizard_step == 0
        assert trip.wizard_started_at is None

    def test_draft_trip_flag(self):
        trip = TripFactory(wizard_completed=False, wizard_step=2)
        trip.refresh_from_db()
        assert trip.wizard_completed is False
        assert trip.wizard_step == 2


class TestDraftExclusionFromListings(TestCase):
    def test_get_trips_excludes_draft(self):
        user = self.make_user("u@example.com")
        TripFactory(author=user, wizard_completed=False)
        context = get_trips(user)
        assert list(context["other_trips"]) == []
        assert context["fav_trip"] is None
        assert context["latest_trip"] is None

    def test_get_trips_exposes_abandoned_draft(self):
        user = self.make_user("u@example.com")
        draft = TripFactory(author=user, wizard_completed=False)
        context = get_trips(user)
        assert context["wizard_draft"] == draft

    def test_get_trips_no_draft_returns_none(self):
        user = self.make_user("u@example.com")
        TripFactory(author=user)
        context = get_trips(user)
        assert context["wizard_draft"] is None

    def test_trip_list_excludes_draft(self):
        user = self.make_user("u@example.com")
        completed = TripFactory(author=user)
        TripFactory(author=user, wizard_completed=False)
        with self.login(user):
            response = self.get("trips:trip-list")
        assert list(response.context["active_trips"]) == [completed]


class TestWizardGating(TestCase):
    def test_has_own_ai_key_true(self):
        creds = AICredentialsFactory()
        assert has_own_ai_key(creds.user) is True

    def test_has_own_ai_key_false_without_key(self):
        user = self.make_user("u@example.com")
        assert has_own_ai_key(user) is False

    def test_has_own_ai_key_false_with_empty_key(self):
        creds = AICredentialsFactory(api_key_encrypted="")
        assert has_own_ai_key(creds.user) is False


class TestCleanupAbandonedWizardTrips(TestCase):
    def test_deletes_old_draft(self):
        user = self.make_user("u@example.com")
        stale = TripFactory(author=user, wizard_completed=False)
        Trip.objects.filter(pk=stale.pk).update(
            wizard_started_at=timezone.now() - timedelta(hours=25)
        )
        deleted = cleanup_abandoned_wizard_trips()
        assert deleted == 1
        assert not Trip.objects.filter(pk=stale.pk).exists()

    def test_keeps_recent_draft(self):
        user = self.make_user("u@example.com")
        recent = TripFactory(author=user, wizard_completed=False)
        Trip.objects.filter(pk=recent.pk).update(
            wizard_started_at=timezone.now() - timedelta(hours=1)
        )
        cleanup_abandoned_wizard_trips()
        assert Trip.objects.filter(pk=recent.pk).exists()

    def test_keeps_completed_trip(self):
        user = self.make_user("u@example.com")
        completed = TripFactory(author=user, wizard_completed=True)
        Trip.objects.filter(pk=completed.pk).update(
            wizard_started_at=timezone.now() - timedelta(hours=25)
        )
        cleanup_abandoned_wizard_trips()
        assert Trip.objects.filter(pk=completed.pk).exists()
