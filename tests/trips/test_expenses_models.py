from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError

from accounts.models import Profile
from trips import models as trip_models
from trips.models import Event, Expense, ExpenseParticipant

pytestmark = pytest.mark.django_db


class TestCurrencyChoices:
    def test_trip_currency_choices_match_profile(self):
        assert trip_models.CURRENCY_CHOICES == Profile.CURRENCY_CHOICES

    def test_trip_expense_defaults(self, trip_factory):
        trip = trip_factory()
        assert trip.expenses_enabled is False
        assert trip.expense_currency == "EUR"


class TestFamilyUnit:
    def test_display_name_uses_explicit_name(self, family_unit_factory):
        unit = family_unit_factory(name="Rossi")
        assert unit.display_name == "Rossi"

    def test_display_name_falls_back_to_first_adult(
        self, family_unit_factory, expense_participant_factory
    ):
        unit = family_unit_factory(name="")
        expense_participant_factory(
            trip=unit.trip, family_unit=unit, is_child=False, name_snapshot="Marco"
        )
        assert "Marco" in unit.display_name

    def test_display_name_without_members(self, family_unit_factory):
        unit = family_unit_factory(name="")
        assert unit.display_name == "Family unit"

    def test_str(self, family_unit_factory):
        unit = family_unit_factory(name="Rossi")
        assert unit.trip.title in str(unit)


class TestExpenseParticipant:
    def test_display_name_from_snapshot(self, expense_participant_factory):
        participant = expense_participant_factory(name_snapshot="Bimbo")
        assert participant.display_name == "Bimbo"

    def test_display_name_from_user(self, trip_factory, user_factory):
        user = user_factory()
        user.profile.first_name = "Enrico"
        user.profile.save()
        trip = trip_factory(author=user)
        participant = ExpenseParticipant.objects.create(
            trip=trip, user=user, name_snapshot="ignored"
        )
        assert participant.display_name == "Enrico"

    def test_display_name_from_collaboration(self, trip_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        collab = TripCollaboration.objects.create(
            trip=trip,
            participant_name="Zia Ada",
            color="blue",
            added_by=trip.author,
        )
        participant = ExpenseParticipant.objects.create(
            trip=trip, collaboration=collab, name_snapshot="stale"
        )
        assert participant.display_name == "Zia Ada"

    def test_str(self, expense_participant_factory):
        participant = expense_participant_factory(name_snapshot="Bimbo")
        assert "Bimbo" in str(participant)


class TestExpenseLinking:
    def _make_participant(self, trip):
        return ExpenseParticipant.objects.create(trip=trip, name_snapshot="P")

    def _linked_expense(self, trip, obj):
        expense = Expense(
            trip=trip,
            title="X",
            amount=Decimal("10.00"),
            date=trip.start_date,
            payer=self._make_participant(trip),
        )
        expense.content_object = obj
        expense.save()
        return expense

    def test_experience_content_type_normalized_to_event(self, experience_factory):
        experience = experience_factory()
        expense = self._linked_expense(experience.trip, experience)
        assert expense.content_type == ContentType.objects.get_for_model(Event)
        assert expense.is_linked is True

    def test_free_expense_is_not_linked(self, trip_factory):
        trip = trip_factory()
        expense = Expense.objects.create(
            trip=trip,
            title="Taxi",
            amount=Decimal("15.00"),
            date=trip.start_date,
            payer=self._make_participant(trip),
        )
        assert expense.is_linked is False

    def test_str(self, trip_factory):
        trip = trip_factory()
        expense = Expense.objects.create(
            trip=trip,
            title="Taxi",
            amount=Decimal("15.00"),
            date=trip.start_date,
            payer=self._make_participant(trip),
        )
        assert "Taxi" in str(expense)


class TestExpenseShare:
    def test_unique_constraint(self, expense_factory, expense_participant_factory):
        expense = expense_factory()
        participant = expense_participant_factory(trip=expense.trip)
        from trips.models import ExpenseShare

        ExpenseShare.objects.create(expense=expense, participant=participant)
        with pytest.raises(IntegrityError):
            ExpenseShare.objects.create(expense=expense, participant=participant)

    def test_str(self, expense_factory, expense_participant_factory):
        expense = expense_factory()
        participant = expense_participant_factory(
            trip=expense.trip, name_snapshot="Anna"
        )
        from trips.models import ExpenseShare

        share = ExpenseShare.objects.create(expense=expense, participant=participant)
        assert "Anna" in str(share)


class TestUnlinkOnDelete:
    def _linked_expense(self, trip, obj):
        participant = ExpenseParticipant.objects.create(trip=trip, name_snapshot="P")
        expense = Expense(
            trip=trip,
            title="X",
            amount=Decimal("10.00"),
            date=trip.start_date,
            payer=participant,
        )
        expense.content_object = obj
        expense.save()
        return expense

    def test_deleting_event_keeps_expense_free_standing(self, meal_factory):
        meal = meal_factory()
        expense = self._linked_expense(meal.trip, meal)
        assert expense.is_linked is True
        meal.delete()
        expense.refresh_from_db()
        assert expense.content_type is None
        assert expense.object_id is None
        assert expense.is_linked is False

    def test_deleting_stay_keeps_expense(self, stay_factory, trip_factory):
        trip = trip_factory()
        stay = stay_factory(day=trip.days.first())
        expense = self._linked_expense(trip, stay)
        stay.delete()
        expense.refresh_from_db()
        assert expense.content_type is None

    def test_deleting_transfer_keeps_expense(self, main_transfer_factory):
        transfer = main_transfer_factory()
        expense = self._linked_expense(transfer.trip, transfer)
        transfer.delete()
        expense.refresh_from_db()
        assert expense.content_type is None
