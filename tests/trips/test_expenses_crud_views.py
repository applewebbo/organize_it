import pytest
from django.urls import reverse

from trips.expenses import ensure_expense_participants
from trips.models import (
    Expense,
    ExpenseParticipant,
    ExpenseShare,
    TripCollaboration,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def crud_trip(authenticated_user, trip_factory):
    user, client = authenticated_user
    trip = trip_factory(author=user, expenses_enabled=True)
    for name in ("Anna", "Bruno"):
        TripCollaboration.objects.create(
            trip=trip,
            participant_name=name,
            color=TripCollaboration.next_free_color(trip),
            added_by=user,
        )
    ensure_expense_participants(trip)
    p1, p2 = trip.expense_participants.filter(collaboration__isnull=False).order_by(
        "created_at"
    )
    return trip, user, client, p1, p2


class TestExpenseCreate:
    def test_get_renders(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        url = reverse("trips:expense-create", args=[trip.pk])
        assert client.get(url).status_code == 200

    def test_post_creates_free_expense(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.post(
            url,
            {
                "title": "Taxi",
                "amount": "20.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                "shared_with": [p1.pk, p2.pk],
            },
        )
        assert response.status_code == 204
        assert response.headers["HX-Trigger"] == "expensesModified"
        expense = Expense.objects.get(title="Taxi")
        assert expense.created_by == user
        assert expense.shares.count() == 2

    def test_get_prefills_payer_with_current_user(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        author_participant = trip.expense_participants.get(user=user)
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.get(url)
        assert response.context["form"].initial["payer"] == author_participant.pk

    def test_post_linked_to_meal(self, crud_trip, meal_factory):
        trip, user, client, p1, p2 = crud_trip
        meal = meal_factory(trip=trip)
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.post(
            f"{url}?ct=event&obj={meal.pk}",
            {
                "title": "Dinner",
                "amount": "40.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                "shared_with": [p1.pk],
            },
        )
        assert response.status_code == 204
        expense = Expense.objects.get(title="Dinner")
        assert expense.is_linked is True
        assert expense.object_id == meal.pk

    def test_post_linked_to_stay(self, crud_trip, stay_factory):
        trip, user, client, p1, p2 = crud_trip
        stay = stay_factory(day=trip.days.first())
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.post(
            f"{url}?ct=stay&obj={stay.pk}",
            {
                "title": "Hotel",
                "amount": "100.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                "shared_with": [p1.pk],
            },
        )
        assert response.status_code == 204
        assert Expense.objects.get(title="Hotel").object_id == stay.pk

    def test_post_linked_to_transfer(self, crud_trip, main_transfer_factory):
        trip, user, client, p1, p2 = crud_trip
        transfer = main_transfer_factory(trip=trip)
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.post(
            f"{url}?ct=transfer&obj={transfer.pk}",
            {
                "title": "Flight",
                "amount": "200.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                "shared_with": [p1.pk],
            },
        )
        assert response.status_code == 204
        assert Expense.objects.get(title="Flight").object_id == transfer.pk

    def test_default_date_for_linked_event(self, crud_trip, meal_factory):
        trip, user, client, p1, p2 = crud_trip
        meal = meal_factory(trip=trip)
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.get(f"{url}?ct=event&obj={meal.pk}")
        assert response.context["form"].initial["date"] == meal.day.date

    def test_default_date_for_linked_stay(self, crud_trip, stay_factory):
        trip, user, client, p1, p2 = crud_trip
        stay = stay_factory(day=trip.days.first())
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.get(f"{url}?ct=stay&obj={stay.pk}")
        assert response.context["form"].initial["date"] == trip.days.first().date

    def test_default_date_for_departure_transfer(
        self, crud_trip, main_transfer_factory
    ):
        trip, user, client, p1, p2 = crud_trip
        transfer = main_transfer_factory(
            trip=trip, direction=2
        )  # DEPARTURE -> trip end
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.get(f"{url}?ct=transfer&obj={transfer.pk}")
        assert response.context["form"].initial["date"] == trip.end_date

    def test_default_date_for_arrival_transfer(self, crud_trip, main_transfer_factory):
        trip, user, client, p1, p2 = crud_trip
        transfer = main_transfer_factory(
            trip=trip, direction=1
        )  # ARRIVAL -> trip start
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.get(f"{url}?ct=transfer&obj={transfer.pk}")
        assert response.context["form"].initial["date"] == trip.start_date

    def test_invalid_ct_returns_404(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        url = reverse("trips:expense-create", args=[trip.pk])
        assert client.get(f"{url}?ct=bogus&obj=1").status_code == 404

    def test_invalid_form_rerenders(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        url = reverse("trips:expense-create", args=[trip.pk])
        response = client.post(
            url,
            {
                "title": "Taxi",
                "amount": "20.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                # no shared_with -> invalid
            },
        )
        assert response.status_code == 200
        assert not Expense.objects.filter(title="Taxi").exists()

    def test_non_editor_404(self, authenticated_user, trip_factory, user_factory):
        user, client = authenticated_user
        other = trip_factory(author=user_factory())
        url = reverse("trips:expense-create", args=[other.pk])
        assert client.get(url).status_code == 404


class TestExpenseModify:
    def test_get_renders_with_initial_shares(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        expense = Expense.objects.create(
            trip=trip, title="X", amount="20.00", date=trip.start_date, payer=p1
        )
        ExpenseShare.objects.create(expense=expense, participant=p1)
        url = reverse("trips:expense-modify", args=[expense.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert list(response.context["form"].initial["shared_with"]) == [p1.pk]

    def test_post_updates_and_resets_shares(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        expense = Expense.objects.create(
            trip=trip, title="X", amount="20.00", date=trip.start_date, payer=p1
        )
        ExpenseShare.objects.create(expense=expense, participant=p1)
        url = reverse("trips:expense-modify", args=[expense.pk])
        response = client.post(
            url,
            {
                "title": "Updated",
                "amount": "30.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                "shared_with": [p1.pk, p2.pk],
            },
        )
        assert response.status_code == 204
        expense.refresh_from_db()
        assert expense.title == "Updated"
        assert expense.shares.count() == 2

    def test_post_invalid_rerenders(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        expense = Expense.objects.create(
            trip=trip, title="X", amount="20.00", date=trip.start_date, payer=p1
        )
        ExpenseShare.objects.create(expense=expense, participant=p1)
        url = reverse("trips:expense-modify", args=[expense.pk])
        response = client.post(
            url,
            {
                "title": "Updated",
                "amount": "30.00",
                "date": trip.start_date.isoformat(),
                "payer": p1.pk,
                # no shared_with -> clean_shared_with fails
            },
        )
        assert response.status_code == 200
        expense.refresh_from_db()
        assert expense.title == "X"


class TestExpenseDelete:
    def test_delete(self, crud_trip):
        trip, user, client, p1, p2 = crud_trip
        expense = Expense.objects.create(
            trip=trip, title="X", amount="20.00", date=trip.start_date, payer=p1
        )
        url = reverse("trips:expense-delete", args=[expense.pk])
        response = client.post(url)
        assert response.status_code == 204
        assert not Expense.objects.filter(pk=expense.pk).exists()

    def test_delete_non_editor_404(
        self, authenticated_user, trip_factory, user_factory
    ):
        user, client = authenticated_user
        other = trip_factory(author=user_factory())
        p = ExpenseParticipant.objects.create(trip=other, name_snapshot="X")
        expense = Expense.objects.create(
            trip=other, title="X", amount="20.00", date=other.start_date, payer=p
        )
        url = reverse("trips:expense-delete", args=[expense.pk])
        assert client.post(url).status_code == 404
