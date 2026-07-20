from decimal import Decimal

import pytest

from trips.expenses import (
    build_expense_summary,
    totals_by_day,
    trip_total,
)
from trips.models import Expense, ExpenseParticipant, ExpenseShare, FamilyUnit

pytestmark = pytest.mark.django_db

D = Decimal


def _participant(trip, name, is_child=False, unit=None):
    return ExpenseParticipant.objects.create(
        trip=trip,
        name_snapshot=name,
        is_child=is_child,
        family_unit=unit,
    )


def _expense(trip, payer, sharers, amount, **kwargs):
    expense = Expense.objects.create(
        trip=trip, title="X", amount=amount, date=trip.start_date, payer=payer, **kwargs
    )
    for participant in sharers:
        ExpenseShare.objects.create(expense=expense, participant=participant)
    return expense


class TestBuildExpenseSummary:
    def test_summary_structure_and_totals(self, trip_factory):
        trip = trip_factory(expense_currency="USD")
        anna = _participant(trip, "Anna")
        bruno = _participant(trip, "Bruno")
        _expense(trip, anna, [anna, bruno], D("30.00"))
        summary = build_expense_summary(trip)
        assert summary["currency"] == "USD"
        assert summary["total"] == D("30.00")
        # Bruno owes Anna 15
        assert summary["settlements"] == [
            {"from_label": "Bruno", "to_label": "Anna", "amount": D("15.00")}
        ]
        assert {row["label"] for row in summary["balances"]} == {"Anna", "Bruno"}
        assert summary["warnings"] == []

    def test_settlement_uses_unit_label(self, trip_factory):
        trip = trip_factory()
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi", shared_wallet=True)
        marco = _participant(trip, "Marco", unit=unit)
        laura = _participant(trip, "Laura", unit=unit)
        carla = _participant(trip, "Carla")
        # unit pays for everyone; Carla owes the unit
        _expense(trip, marco, [marco, laura, carla], D("30.00"))
        summary = build_expense_summary(trip)
        assert summary["settlements"] == [
            {"from_label": "Carla", "to_label": "Rossi", "amount": D("10.00")}
        ]

    def test_balances_grouped_by_family(self, trip_factory):
        trip = trip_factory()
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi")
        marco = _participant(trip, "Marco", unit=unit)
        laura = _participant(trip, "Laura", unit=unit)
        carla = _participant(trip, "Carla")
        _expense(trip, marco, [marco, laura, carla], D("30.00"))
        summary = build_expense_summary(trip)
        rows = {row["label"]: row for row in summary["balances"]}
        assert set(rows) == {"Rossi", "Carla"}
        # Rossi paid 30 and consumed their two shares (20): net +10.
        assert rows["Rossi"]["paid"] == D("30.00")
        assert rows["Rossi"]["owed"] == D("20.00")
        assert rows["Rossi"]["net"] == D("10.00")
        assert rows["Carla"]["net"] == D("-10.00")

    def test_warning_for_child_without_unit(self, trip_factory):
        trip = trip_factory()
        anna = _participant(trip, "Anna")
        kid = _participant(trip, "Kid", is_child=True)
        _expense(trip, anna, [anna, kid], D("20.00"))
        summary = build_expense_summary(trip)
        assert [p.pk for p in summary["warnings"]] == [kid.pk]

    def test_shareless_expense_ignored_in_balances(self, trip_factory):
        trip = trip_factory()
        anna = _participant(trip, "Anna")
        Expense.objects.create(
            trip=trip,
            title="orphan",
            amount=D("5.00"),
            date=trip.start_date,
            payer=anna,
        )
        summary = build_expense_summary(trip)
        assert summary["settlements"] == []
        # still counted in the overall total
        assert summary["total"] == D("5.00")


class TestTotals:
    def test_trip_total_empty(self, trip_factory):
        trip = trip_factory()
        assert trip_total(trip) == D("0.00")

    def test_totals_by_day_maps_day_number(self, trip_factory):
        trip = trip_factory()
        anna = _participant(trip, "Anna")
        first_day = trip.days.first()
        Expense.objects.create(
            trip=trip,
            title="X",
            amount=D("10.00"),
            date=first_day.date,
            payer=anna,
        )
        totals = totals_by_day(trip)
        assert totals[0]["day_number"] == first_day.number
        assert totals[0]["total"] == D("10.00")
