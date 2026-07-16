import pytest
from django.urls import reverse

from trips.expenses import ensure_expense_participants
from trips.models import Expense, ExpenseShare, TripCollaboration

pytestmark = pytest.mark.django_db


def _setup_expense(trip, author_user):
    """Author pays 30 shared with a named participant -> the named owes 15."""
    TripCollaboration.objects.create(
        trip=trip,
        participant_name="Anna",
        color=TripCollaboration.next_free_color(trip),
        added_by=author_user,
    )
    ensure_expense_participants(trip)
    author_p = trip.expense_participants.get(user=author_user)
    anna_p = trip.expense_participants.get(collaboration__isnull=False)
    expense = Expense.objects.create(
        trip=trip, title="Dinner", amount="30.00", date=trip.start_date, payer=author_p
    )
    ExpenseShare.objects.create(expense=expense, participant=author_p)
    ExpenseShare.objects.create(expense=expense, participant=anna_p)
    return author_p, anna_p


class TestExpensesCard:
    def test_disabled_shows_cta(self, authenticated_user, trip_factory):
        user, client = authenticated_user
        trip = trip_factory(author=user, expenses_enabled=False)
        url = reverse("trips:expenses-card", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert "summary" not in response.context
        assert b"Enable expense sharing" in response.content

    def test_enabled_shows_totals_and_user_net(self, authenticated_user, trip_factory):
        user, client = authenticated_user
        trip = trip_factory(author=user, expenses_enabled=True)
        _setup_expense(trip, user)
        url = reverse("trips:expenses-card", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["summary"]["total"] == __import__("decimal").Decimal(
            "30.00"
        )
        # author paid 30, owes 15 -> net +15 (is owed)
        assert response.context["user_net"] > 0

    def test_stranger_404(self, authenticated_user, trip_factory, user_factory):
        user, client = authenticated_user
        other = trip_factory(author=user_factory(), expenses_enabled=True)
        url = reverse("trips:expenses-card", args=[other.pk])
        assert client.get(url).status_code == 404


class TestExpensesModal:
    def test_renders_tabs_and_data(self, authenticated_user, trip_factory):
        user, client = authenticated_user
        trip = trip_factory(author=user, expenses_enabled=True)
        _setup_expense(trip, user)
        url = reverse("trips:expenses-modal", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Dinner" in content
        assert "Balances" in content
        assert "Totals" in content

    def test_stranger_404(self, authenticated_user, trip_factory, user_factory):
        user, client = authenticated_user
        other = trip_factory(author=user_factory(), expenses_enabled=True)
        url = reverse("trips:expenses-modal", args=[other.pk])
        assert client.get(url).status_code == 404
