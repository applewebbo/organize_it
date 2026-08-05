from datetime import date

import pytest
from django.test import override_settings

from tests.suggestions.factories import AICredentialsFactory
from tests.test import TestCase
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db


def _draft(author, step=2):
    return TripFactory(
        author=author,
        destination="Roma",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        wizard_completed=False,
        wizard_step=step,
    )


class TestWizardStays(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        self.response_302(self.get("trips:wizard-stays", pk=trip.pk))

    def test_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        trip = _draft(user)
        with self.login(user):
            response = self.get("trips:wizard-stays", pk=trip.pk)
        assert response.status_code == 403

    def test_post_not_allowed(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            response = self.post("trips:wizard-stays", pk=trip.pk)
        assert response.status_code == 405

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        AICredentialsFactory(user=owner)
        other = self.make_user("other@example.com")
        AICredentialsFactory(user=other)
        trip = _draft(owner)
        with self.login(other):
            self.response_404(self.get("trips:wizard-stays", pk=trip.pk))

    def test_renders_and_advances_step(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user, step=2)
        with self.login(user):
            response = self.get("trips:wizard-stays", pk=trip.pk)
        self.response_200(response)
        assert "Where will you stay?" in response.content.decode()
        trip.refresh_from_db()
        assert trip.wizard_step == 3

    def test_keeps_step_when_already_on_stays(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user, step=3)
        with self.login(user):
            response = self.get("trips:wizard-stays", pk=trip.pk)
        self.response_200(response)
        trip.refresh_from_db()
        assert trip.wizard_step == 3

    @override_settings(STAY22_AID="test-aid")
    def test_lists_stages_when_stay22_available(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            response = self.get("trips:wizard-stays", pk=trip.pk)
        content = response.content.decode()
        assert "Roma" in content
        assert f"/trips/{trip.pk}/booking/" in content

    @override_settings(STAY22_AID="")
    def test_shows_unavailable_note_without_stay22(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            response = self.get("trips:wizard-stays", pk=trip.pk)
        assert "currently unavailable" in response.content.decode()


class TestWizardResume(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        self.response_302(self.get("trips:wizard-resume", pk=trip.pk))

    def test_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        trip = _draft(user)
        with self.login(user):
            response = self.get("trips:wizard-resume", pk=trip.pk)
        assert response.status_code == 403

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        AICredentialsFactory(user=owner)
        other = self.make_user("other@example.com")
        AICredentialsFactory(user=other)
        trip = _draft(owner)
        with self.login(other):
            self.response_404(self.get("trips:wizard-resume", pk=trip.pk))

    def test_resumes_at_ai_step(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user, step=2)
        with self.login(user):
            response = self.get("trips:wizard-resume", pk=trip.pk)
        content = response.content.decode()
        assert "AI day planning" in content
        assert "wizardExitGuard(true)" in content

    def test_resumes_at_stays_step(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user, step=3)
        with self.login(user):
            response = self.get("trips:wizard-resume", pk=trip.pk)
        assert "Where will you stay?" in response.content.decode()
