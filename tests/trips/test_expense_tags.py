from decimal import Decimal

import pytest
from django.template.loader import render_to_string

from trips.models import Expense, ExpenseParticipant
from trips.templatetags.expense_tags import linked_expense, money

pytestmark = pytest.mark.django_db


class TestMoneyFilter:
    def test_eur_symbol(self):
        assert money(Decimal("12.50"), "EUR") == "€ 12.50"

    def test_usd_symbol(self):
        assert money(Decimal("5"), "USD") == "$ 5.00"

    def test_unknown_currency_uses_code(self):
        assert money(Decimal("1.00"), "CHF") == "CHF 1.00"

    def test_none_amount_is_zero(self):
        assert money(None, "GBP") == "£ 0.00"


class TestLinkedExpenseTag:
    def test_returns_linked_expense_for_meal(self, trip_factory, meal_factory):
        trip = trip_factory()
        meal = meal_factory(trip=trip)
        participant = ExpenseParticipant.objects.create(trip=trip, name_snapshot="P")
        expense = Expense(
            trip=trip,
            title="Dinner",
            amount=Decimal("10.00"),
            date=trip.start_date,
            payer=participant,
        )
        expense.content_object = meal
        expense.save()
        assert linked_expense(meal) == expense

    def test_returns_none_when_unlinked(self, meal_factory):
        assert linked_expense(meal_factory()) is None

    def test_returns_none_for_none(self):
        assert linked_expense(None) is None


class TestCostRowInclude:
    def _render(self, obj, trip):
        return render_to_string(
            "trips/includes/_expense-cost-row.html",
            {"obj": obj, "trip": trip, "ct": "event"},
        )

    def test_hidden_when_disabled(self, trip_factory, meal_factory):
        trip = trip_factory(expenses_enabled=False)
        assert self._render(meal_factory(trip=trip), trip).strip() == ""

    def test_add_button_when_unlinked(self, trip_factory, meal_factory):
        trip = trip_factory(expenses_enabled=True)
        assert "Add cost" in self._render(meal_factory(trip=trip), trip)

    def test_shows_amount_when_linked(self, trip_factory, meal_factory):
        trip = trip_factory(expenses_enabled=True)
        meal = meal_factory(trip=trip)
        participant = ExpenseParticipant.objects.create(trip=trip, name_snapshot="P")
        expense = Expense(
            trip=trip,
            title="x",
            amount=Decimal("12.00"),
            date=trip.start_date,
            payer=participant,
        )
        expense.content_object = meal
        expense.save()
        assert "12.00" in self._render(meal, trip)
