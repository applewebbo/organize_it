import pytest
from django.urls import reverse

from trips.expenses import ensure_expense_participants
from trips.models import Expense, ExpenseShare, TripCollaboration
from trips.views.expenses import _user_net

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
        assert b"Track who paid for what" in response.content

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

    def test_user_net_none_for_child_participant(
        self, authenticated_user, trip_factory, user_factory
    ):
        # A collaborator marked as child is attributed to a parent, so their
        # own balance is absent and the card shows no personal balance line.
        from trips.models import FamilyUnit, TripCollaboration

        author = user_factory()
        trip = trip_factory(author=author, expenses_enabled=True)
        child_user, client = authenticated_user
        TripCollaboration.objects.create(
            trip=trip,
            user=child_user,
            color=TripCollaboration.next_free_color(trip),
            added_by=author,
        )
        ensure_expense_participants(trip)
        unit = FamilyUnit.objects.create(trip=trip, name="Rossi")
        author_p = trip.expense_participants.get(user=author)
        author_p.family_unit = unit
        author_p.save()
        child_p = trip.expense_participants.get(user=child_user)
        child_p.is_child = True
        child_p.family_unit = unit
        child_p.save()
        Expense.objects.create(
            trip=trip, title="X", amount="10.00", date=trip.start_date, payer=author_p
        )
        url = reverse("trips:expenses-card", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["user_net"] is None


class TestUserNet:
    def test_none_for_non_participant(self, trip_factory, user_factory):
        trip = trip_factory(expenses_enabled=True)
        stranger = user_factory()
        assert _user_net(trip, stranger, {"nets_by_participant": {}}) is None


class TestExpenseToggle:
    def test_enable_sets_currency_from_author(self, authenticated_user, trip_factory):
        user, client = authenticated_user
        user.profile.currency = "USD"
        user.profile.save()
        trip = trip_factory(author=user, expenses_enabled=False)
        url = reverse("trips:expense-toggle", args=[trip.pk])
        response = client.post(url, {"expenses_enabled": "on"})
        assert response.status_code == 200
        trip.refresh_from_db()
        assert trip.expenses_enabled is True
        assert trip.expense_currency == "USD"
        assert "summary" in response.context

    def test_disable(self, authenticated_user, trip_factory):
        user, client = authenticated_user
        trip = trip_factory(author=user, expenses_enabled=True)
        url = reverse("trips:expense-toggle", args=[trip.pk])
        response = client.post(url, {})
        assert response.status_code == 200
        trip.refresh_from_db()
        assert trip.expenses_enabled is False

    def test_non_editor_404(self, authenticated_user, trip_factory, user_factory):
        user, client = authenticated_user
        other = trip_factory(author=user_factory(), expenses_enabled=False)
        url = reverse("trips:expense-toggle", args=[other.pk])
        assert client.post(url, {"expenses_enabled": "on"}).status_code == 404


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
