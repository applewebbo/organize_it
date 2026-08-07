from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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


class TestWizardEntryPoint(TestCase):
    def test_trip_list_shows_wizard_link_with_key(self):
        user = self.make_user("u@example.com")
        AICredentialsFactory(user=user)
        TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-list")
        assert response.context["wizard_available"] is True
        self.assertContains(response, "trips/wizard/")

    def test_trip_list_hides_wizard_link_without_key(self):
        user = self.make_user("u@example.com")
        TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-list")
        assert response.context["wizard_available"] is False
        self.assertNotContains(response, "trips/wizard/")


class TestAutoSelectedCoverBadge(TestCase):
    """The AI badge marks covers picked by the wizard (issue #422)."""

    BADGE = "cover-ai-badge"

    def _trip_with_cover(self, author, metadata):
        trip = TripFactory(author=author, image_metadata=metadata)
        trip.image.save(
            "cover.jpg",
            SimpleUploadedFile("cover.jpg", b"data", content_type="image/jpeg"),
            save=True,
        )
        return trip

    def test_detail_shows_badge_on_auto_selected_cover(self):
        user = self.make_user("owner@example.com")
        trip = self._trip_with_cover(
            user, {"source": "unsplash", "auto_selected": True, "photographer": "T"}
        )
        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)
        self.assertContains(response, self.BADGE)

    def test_detail_hides_badge_on_manually_picked_cover(self):
        user = self.make_user("owner@example.com")
        trip = self._trip_with_cover(user, {"source": "unsplash", "photographer": "T"})
        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)
        self.assertNotContains(response, self.BADGE)

    def test_image_status_fragment_shows_badge_when_ready(self):
        user = self.make_user("owner@example.com")
        trip = self._trip_with_cover(
            user, {"source": "unsplash", "auto_selected": True}
        )
        with self.login(user):
            response = self.get("trips:trip-image-status", pk=trip.pk)
        self.assertContains(response, self.BADGE)

    def test_image_status_fragment_hides_badge_while_pending(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(
            author=user,
            image_metadata={
                "source": "unsplash",
                "pending": True,
                "auto_selected": True,
            },
        )
        with self.login(user):
            response = self.get("trips:trip-image-status", pk=trip.pk)
        self.assertNotContains(response, self.BADGE)


def _draft(author, **kwargs):
    return TripFactory(author=author, wizard_completed=False, wizard_step=3, **kwargs)


class TestWizardFinish(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        self.response_302(self.post("trips:wizard-finish", pk=trip.pk))

    def test_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        trip = _draft(user)
        with self.login(user):
            response = self.post("trips:wizard-finish", pk=trip.pk)
        assert response.status_code == 403

    def test_get_not_allowed(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            response = self.get("trips:wizard-finish", pk=trip.pk)
        assert response.status_code == 405

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        AICredentialsFactory(user=owner)
        other = self.make_user("other@example.com")
        AICredentialsFactory(user=other)
        trip = _draft(owner)
        with self.login(other):
            self.response_404(self.post("trips:wizard-finish", pk=trip.pk))

    def test_marks_completed_and_redirects_to_trip(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user), patch("trips.views.wizard.async_task"):
            response = self.post("trips:wizard-finish", pk=trip.pk)
        self.assertRedirects(
            response, f"/trips/{trip.pk}", fetch_redirect_response=False
        )
        trip.refresh_from_db()
        assert trip.wizard_completed is True

    def test_schedules_auto_cover_when_trip_has_no_image(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user, destination="Lisbon")
        with self.login(user), patch("trips.views.wizard.async_task") as mock_task:
            self.post("trips:wizard-finish", pk=trip.pk)

        mock_task.assert_called_once_with("trips.tasks.auto_select_trip_cover", trip.pk)
        trip.refresh_from_db()
        assert trip.image_metadata == {
            "source": "unsplash",
            "pending": True,
            "auto_selected": True,
        }

    def test_does_not_schedule_auto_cover_when_image_already_uploaded(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user, image_metadata={"source": "upload"})
        trip.image.save(
            "cover.jpg",
            SimpleUploadedFile("cover.jpg", b"data", content_type="image/jpeg"),
            save=True,
        )
        with self.login(user), patch("trips.views.wizard.async_task") as mock_task:
            self.post("trips:wizard-finish", pk=trip.pk)

        mock_task.assert_not_called()
        trip.refresh_from_db()
        assert trip.image_metadata == {"source": "upload"}


class TestWizardCancel(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        self.response_302(self.post("trips:wizard-cancel", pk=trip.pk))

    def test_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        trip = _draft(user)
        with self.login(user):
            response = self.post("trips:wizard-cancel", pk=trip.pk)
        assert response.status_code == 403

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        AICredentialsFactory(user=owner)
        other = self.make_user("other@example.com")
        AICredentialsFactory(user=other)
        trip = _draft(owner)
        with self.login(other):
            self.response_404(self.post("trips:wizard-cancel", pk=trip.pk))

    def test_deletes_draft_and_redirects_home(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            response = self.post("trips:wizard-cancel", pk=trip.pk)
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        assert not Trip.objects.filter(pk=trip.pk).exists()


class TestWizardResumeBanner(TestCase):
    def test_home_shows_resume_banner_for_draft(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        draft = TripFactory(
            author=user, wizard_completed=False, wizard_step=2, title="Draft Trip"
        )
        with self.login(user):
            response = self.get("trips:home")
        content = response.content.decode()
        assert "Draft Trip" in content
        assert f"/trips/wizard/{draft.pk}/resume/" in content

    def test_home_no_banner_without_draft(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:home")
        assert "/resume/" not in response.content.decode()


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
