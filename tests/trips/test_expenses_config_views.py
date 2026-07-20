import json

import pytest
from django.urls import reverse

from trips.models import ExpenseParticipant, FamilyUnit

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor_trip(authenticated_user, trip_factory):
    user, client = authenticated_user
    trip = trip_factory(author=user, expenses_enabled=True)
    return trip, user, client


class TestExpenseSettings:
    def test_get_creates_participants_and_renders(self, editor_trip):
        trip, user, client = editor_trip
        url = reverse("trips:expense-settings", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert ExpenseParticipant.objects.filter(trip=trip, user=user).exists()

    def test_post_enables_and_sets_currency(self, authenticated_user, trip_factory):
        user, client = authenticated_user
        user.profile.currency = "GBP"
        user.profile.save()
        trip = trip_factory(author=user, expenses_enabled=False)
        url = reverse("trips:expense-settings", args=[trip.pk])
        response = client.post(
            url, {"expenses_enabled": "on", "expense_currency": "GBP"}
        )
        assert response.status_code == 200
        assert response.headers["HX-Trigger"] == "expensesModified"
        trip.refresh_from_db()
        assert trip.expenses_enabled is True
        assert trip.expense_currency == "GBP"

    def test_get_initial_currency_from_author_profile(
        self, authenticated_user, trip_factory
    ):
        user, client = authenticated_user
        user.profile.currency = "USD"
        user.profile.save()
        trip = trip_factory(author=user, expenses_enabled=False)
        url = reverse("trips:expense-settings", args=[trip.pk])
        response = client.get(url)
        assert response.context["settings_form"].initial["expense_currency"] == "USD"

    def test_non_editor_gets_404(self, authenticated_user, trip_factory, user_factory):
        user, client = authenticated_user
        other_trip = trip_factory(author=user_factory())
        url = reverse("trips:expense-settings", args=[other_trip.pk])
        assert client.get(url).status_code == 404

    def test_post_invalid_currency_rerenders(self, editor_trip):
        trip, user, client = editor_trip
        url = reverse("trips:expense-settings", args=[trip.pk])
        response = client.post(
            url, {"expenses_enabled": "on", "expense_currency": "XXX"}
        )
        assert response.status_code == 200
        trip.refresh_from_db()
        assert trip.expense_currency != "XXX"


class TestFamilyUnits:
    def test_create(self, editor_trip):
        trip, user, client = editor_trip
        url = reverse("trips:family-unit-create", args=[trip.pk])
        response = client.post(url, {"name": "Rossi"})
        assert response.status_code == 200
        assert FamilyUnit.objects.filter(trip=trip, name="Rossi").exists()

    def test_create_invalid_is_ignored(self, editor_trip):
        trip, user, client = editor_trip
        url = reverse("trips:family-unit-create", args=[trip.pk])
        # name too long -> invalid form, no unit created, still renders config
        response = client.post(url, {"name": "x" * 200})
        assert response.status_code == 200
        assert FamilyUnit.objects.filter(trip=trip).count() == 0

    def test_delete_detaches_members(self, editor_trip):
        trip, user, client = editor_trip
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi")
        participant = ExpenseParticipant.objects.create(
            trip=trip, name_snapshot="Marco", family_unit=unit
        )
        url = reverse("trips:family-unit-delete", args=[unit.pk])
        response = client.post(url)
        assert response.status_code == 200
        participant.refresh_from_db()
        assert participant.family_unit is None
        assert not FamilyUnit.objects.filter(pk=unit.pk).exists()


class TestFamilyUnitAssign:
    def test_json_assign_returns_204(self, editor_trip):
        trip, user, client = editor_trip
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi")
        participant = ExpenseParticipant.objects.create(trip=trip, name_snapshot="M")
        url = reverse("trips:family-unit-assign", args=[trip.pk])
        response = client.post(
            url,
            data=json.dumps({"participant_id": participant.pk, "unit_id": unit.pk}),
            content_type="application/json",
        )
        assert response.status_code == 204
        participant.refresh_from_db()
        assert participant.family_unit == unit

    def test_json_detach(self, editor_trip):
        trip, user, client = editor_trip
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi")
        participant = ExpenseParticipant.objects.create(
            trip=trip, name_snapshot="M", family_unit=unit
        )
        url = reverse("trips:family-unit-assign", args=[trip.pk])
        response = client.post(
            url,
            data=json.dumps({"participant_id": participant.pk, "unit_id": None}),
            content_type="application/json",
        )
        assert response.status_code == 204
        participant.refresh_from_db()
        assert participant.family_unit is None

    def test_form_fallback_renders_config(self, editor_trip):
        trip, user, client = editor_trip
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi")
        participant = ExpenseParticipant.objects.create(trip=trip, name_snapshot="M")
        url = reverse("trips:family-unit-assign", args=[trip.pk])
        response = client.post(
            url, {"participant_id": participant.pk, "unit_id": unit.pk}
        )
        assert response.status_code == 200
        participant.refresh_from_db()
        assert participant.family_unit == unit

    def test_bad_payload_returns_400(self, editor_trip):
        trip, user, client = editor_trip
        url = reverse("trips:family-unit-assign", args=[trip.pk])
        response = client.post(url, data="not-json", content_type="application/json")
        assert response.status_code == 400


class TestToggleChild:
    def test_toggle(self, editor_trip):
        trip, user, client = editor_trip
        participant = ExpenseParticipant.objects.create(trip=trip, name_snapshot="Kid")
        url = reverse("trips:participant-toggle-child", args=[participant.pk])
        response = client.post(url)
        assert response.status_code == 200
        participant.refresh_from_db()
        assert participant.is_child is True
