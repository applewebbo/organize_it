import pytest
from django.urls import reverse

from tests.test import TestCase
from tests.trips.factories import (
    ExperienceFactory,
    MainTransferFactory,
    StayFactory,
    StayTransferFactory,
    TripFactory,
)

pytestmark = pytest.mark.django_db


def _setup_consecutive_days_with_stays(user):
    """Create a trip with 2+ days where day1 and day2 each have a distinct stay."""
    from datetime import date, timedelta

    from trips.models import Trip

    trip = Trip.objects.create(
        author=user,
        title="Test Trip",
        destination="Roma",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=3),
    )
    days = list(trip.days.order_by("date"))
    stay1 = StayFactory(day=days[0])
    stay2 = StayFactory(day=days[1])
    return trip, days, stay1, stay2


class TestCreateStayTransferView(TestCase):
    def test_get_create_form(self):
        """GET request shows the create form"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})

        with self.login(user):
            response = self.client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_post_valid_creates_transfer(self):
        """POST with valid data creates a StayTransfer"""
        from trips.models import StayTransfer

        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})

        data = {"transport_mode": "driving", "notes": ""}
        with self.login(user):
            response = self.client.post(url, data)

        assert response.status_code == 204
        assert StayTransfer.objects.filter(from_stay=stay1, to_stay=stay2).exists()

    def test_post_invalid_returns_form(self):
        """POST with invalid data re-renders form"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})

        # invalid: missing required transport_mode
        data = {"transport_mode": "", "notes": ""}
        with self.login(user):
            response = self.client.post(url, data)

        assert response.status_code == 200

    def test_no_next_day_returns_204(self):
        """Returns 204 with error message when from_day has no next day"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        last_day = days[-1]
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": last_day.pk})

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204

    def test_from_day_without_stay_returns_204(self):
        """Returns 204 with error message when from_day has no stay"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        # Remove stay from day[0]
        days[0].stay = None
        days[0].save()
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204

    def test_same_stay_on_both_days_returns_204(self):
        """Returns 204 with error message when both days share the same stay"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        # Set day[1] to use stay1 too
        days[1].stay = stay1
        days[1].save()
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204


class TestEditStayTransferView(TestCase):
    def test_get_edit_form(self):
        """GET request shows edit form"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        transfer = StayTransferFactory(
            from_stay=stay1,
            to_stay=stay2,
            from_day=days[0],
            to_day=days[1],
            trip=trip,
        )
        url = reverse("trips:edit-stay-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_post_valid_updates_transfer(self):
        """POST with valid data updates transport_mode"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        transfer = StayTransferFactory(
            from_stay=stay1,
            to_stay=stay2,
            from_day=days[0],
            to_day=days[1],
            trip=trip,
            transport_mode="driving",
        )
        url = reverse("trips:edit-stay-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "transit", "notes": ""})

        assert response.status_code == 204
        transfer.refresh_from_db()
        assert transfer.transport_mode == "transit"

    def test_post_invalid_returns_form(self):
        """POST with invalid data re-renders form"""
        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        transfer = StayTransferFactory(
            from_stay=stay1,
            to_stay=stay2,
            from_day=days[0],
            to_day=days[1],
            trip=trip,
        )
        url = reverse("trips:edit-stay-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "", "notes": ""})

        assert response.status_code == 200


class TestDeleteStayTransferView(TestCase):
    def test_delete_removes_transfer(self):
        """DELETE removes the StayTransfer"""
        from trips.models import StayTransfer

        user = self.make_user("user")
        trip, days, stay1, stay2 = _setup_consecutive_days_with_stays(user)
        transfer = StayTransferFactory(
            from_stay=stay1,
            to_stay=stay2,
            from_day=days[0],
            to_day=days[1],
            trip=trip,
        )
        url = reverse("trips:delete-stay-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.post(url)

        assert response.status_code == 204
        assert not StayTransfer.objects.filter(pk=transfer.pk).exists()


class TestMainTransferConnectionViews(TestCase):
    def test_connection_modal_arrival(self):
        """GET modal for ARRIVAL transfer shows available stay/event"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)  # ARRIVAL
        day1 = trip.days.order_by("date").first()
        StayFactory(day=day1)
        ExperienceFactory(trip=trip, day=day1)
        url = reverse(
            "trips:main-transfer-connection-modal",
            kwargs={"main_transfer_pk": transfer.pk},
        )

        with self.login(user):
            response = self.client.get(url)

        assert response.status_code == 200
        assert "main_transfer" in response.context

    def test_connection_modal_departure(self):
        """GET modal for DEPARTURE transfer shows last day options"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=2, type=1)  # DEPARTURE
        last_day = trip.days.order_by("-date").first()
        StayFactory(day=last_day)
        url = reverse(
            "trips:main-transfer-connection-modal",
            kwargs={"main_transfer_pk": transfer.pk},
        )

        with self.login(user):
            response = self.client.get(url)

        assert response.status_code == 200

    def test_connection_modal_shows_existing_connection(self):
        """GET modal shows existing_connection if present"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        conn = MainTransferConnection.objects.create(
            main_transfer=transfer, stay=stay, transport_mode="driving"
        )
        url = reverse(
            "trips:main-transfer-connection-modal",
            kwargs={"main_transfer_pk": transfer.pk},
        )

        with self.login(user):
            response = self.client.get(url)

        assert response.context["existing_connection"] == conn

    def test_create_connection_to_stay_arrival(self):
        """POST creates connection to stay for ARRIVAL transfer"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert MainTransferConnection.objects.filter(
            main_transfer=transfer, stay=stay
        ).exists()

    def test_create_connection_to_event_arrival(self):
        """POST creates connection to event for ARRIVAL transfer"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        event = ExperienceFactory(trip=trip, day=day1)
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "event"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert MainTransferConnection.objects.filter(
            main_transfer=transfer, event=event
        ).exists()

    def test_create_connection_to_stay_departure(self):
        """POST creates connection to stay for DEPARTURE transfer"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=2, type=1)  # DEPARTURE
        last_day = trip.days.order_by("-date").first()
        stay = StayFactory(day=last_day)
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert MainTransferConnection.objects.filter(
            main_transfer=transfer, stay=stay
        ).exists()

    def test_create_connection_to_event_departure(self):
        """POST creates connection to event for DEPARTURE transfer"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=2, type=1)  # DEPARTURE
        last_day = trip.days.order_by("-date").first()
        event = ExperienceFactory(trip=trip, day=last_day)
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "event"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert MainTransferConnection.objects.filter(
            main_transfer=transfer, event=event
        ).exists()

    def test_create_connection_already_exists_returns_error(self):
        """POST returns 204 with refresh if connection already exists"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        MainTransferConnection.objects.create(
            main_transfer=transfer, stay=stay, transport_mode="driving"
        )
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert response.get("HX-Refresh") == "true"

    def test_create_connection_invalid_destination_type(self):
        """POST with invalid destination_type returns 204 with refresh"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "invalid"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert response.get("HX-Refresh") == "true"

    def test_create_connection_no_days_returns_error(self):
        """POST returns 204 when trip has no days"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        trip.days.all().delete()
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert response.get("HX-Refresh") == "true"

    def test_create_connection_no_destination_returns_error(self):
        """POST returns 204 when destination (event/stay) doesn't exist"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        # day1 has no stay
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert response.get("HX-Refresh") == "true"

    def test_create_connection_invalid_form_renders_template(self):
        """POST with invalid form data renders create template"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        StayFactory(day=day1)
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "", "notes": ""})

        assert response.status_code == 200

    def test_edit_connection_get(self):
        """GET edit form shows connection"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        conn = MainTransferConnection.objects.create(
            main_transfer=transfer, stay=stay, transport_mode="driving"
        )
        url = reverse("trips:edit-main-transfer-connection", kwargs={"pk": conn.pk})

        with self.login(user):
            response = self.client.get(url)

        assert response.status_code == 200
        assert response.context["connection"] == conn

    def test_edit_connection_post_valid(self):
        """POST with valid data updates connection"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        conn = MainTransferConnection.objects.create(
            main_transfer=transfer, stay=stay, transport_mode="driving"
        )
        url = reverse("trips:edit-main-transfer-connection", kwargs={"pk": conn.pk})

        with self.login(user):
            response = self.client.post(
                url, {"transport_mode": "transit", "notes": "test"}
            )

        assert response.status_code == 204
        conn.refresh_from_db()
        assert conn.transport_mode == "transit"

    def test_edit_connection_post_invalid(self):
        """POST with invalid data re-renders form"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        conn = MainTransferConnection.objects.create(
            main_transfer=transfer, stay=stay, transport_mode="driving"
        )
        url = reverse("trips:edit-main-transfer-connection", kwargs={"pk": conn.pk})

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "", "notes": ""})

        assert response.status_code == 200

    def test_delete_connection(self):
        """DELETE removes connection"""
        from trips.models import MainTransferConnection

        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        conn = MainTransferConnection.objects.create(
            main_transfer=transfer, stay=stay, transport_mode="driving"
        )
        url = reverse("trips:delete-main-transfer-connection", kwargs={"pk": conn.pk})

        with self.login(user):
            response = self.client.post(url)

        assert response.status_code == 204
        assert not MainTransferConnection.objects.filter(pk=conn.pk).exists()

    def test_create_connection_departure_no_days(self):
        """POST returns 204 when DEPARTURE trip has no days"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=2, type=1)  # DEPARTURE
        trip.days.all().delete()
        url = reverse(
            "trips:create-main-transfer-connection",
            kwargs={"main_transfer_pk": transfer.pk, "destination_type": "stay"},
        )

        with self.login(user):
            response = self.client.post(url, {"transport_mode": "driving", "notes": ""})

        assert response.status_code == 204
        assert response.get("HX-Refresh") == "true"
