"""Tests for SimpleTransfer and StayTransfer views"""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from trips.models import SimpleTransfer, StayTransfer

pytestmark = pytest.mark.django_db


class TestSimpleTransferViews:
    """Tests for SimpleTransfer CRUD views"""

    def test_create_simple_transfer_get(self, client, trip_factory, experience_factory):
        """Test GET request to create simple transfer form"""
        trip = trip_factory()
        day = trip.days.first()
        event1 = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        experience_factory(trip=trip, day=day, start_time="14:00", end_time="15:00")

        client.force_login(trip.author)
        url = reverse(
            "trips:create-simple-transfer", kwargs={"from_event_pk": event1.pk}
        )
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_create_simple_transfer_post(
        self, client, trip_factory, experience_factory
    ):
        """Test POST request to create simple transfer"""
        trip = trip_factory()
        day = trip.days.first()
        event1 = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        experience_factory(trip=trip, day=day, start_time="14:00", end_time="15:00")

        client.force_login(trip.author)
        url = reverse(
            "trips:create-simple-transfer", kwargs={"from_event_pk": event1.pk}
        )
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert SimpleTransfer.objects.filter(from_event=event1).exists()

    def test_create_simple_transfer_no_day(
        self, client, trip_factory, experience_factory
    ):
        """Test creating transfer for event without day"""
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(trip=trip, day=day)
        event.day = None
        event.save()

        client.force_login(trip.author)
        url = reverse(
            "trips:create-simple-transfer", kwargs={"from_event_pk": event.pk}
        )
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers

    def test_create_simple_transfer_no_next_event(
        self, client, trip_factory, experience_factory
    ):
        """Test creating transfer when no next event exists"""
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(
            trip=trip, day=day, start_time="23:00", end_time="23:59"
        )

        client.force_login(trip.author)
        url = reverse(
            "trips:create-simple-transfer", kwargs={"from_event_pk": event.pk}
        )
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers

    def test_edit_simple_transfer_get(self, client, trip_factory, experience_factory):
        """Test GET request to edit simple transfer form"""
        trip = trip_factory()
        day = trip.days.first()
        event1 = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = experience_factory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        transfer = SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        client.force_login(trip.author)
        url = reverse("trips:edit-simple-transfer", kwargs={"pk": transfer.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_edit_simple_transfer_post(self, client, trip_factory, experience_factory):
        """Test POST request to edit simple transfer"""
        trip = trip_factory()
        day = trip.days.first()
        event1 = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = experience_factory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        transfer = SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        client.force_login(trip.author)
        url = reverse("trips:edit-simple-transfer", kwargs={"pk": transfer.pk})
        response = client.post(url, {"transport_mode": "walking", "notes": "Test note"})

        assert response.status_code == 204
        transfer.refresh_from_db()
        assert transfer.transport_mode == "walking"

    def test_delete_simple_transfer(self, client, trip_factory, experience_factory):
        """Test deleting a simple transfer"""
        trip = trip_factory()
        day = trip.days.first()
        event1 = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = experience_factory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        transfer = SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )
        transfer_pk = transfer.pk

        client.force_login(trip.author)
        url = reverse("trips:delete-simple-transfer", kwargs={"pk": transfer.pk})
        response = client.post(url)

        assert response.status_code == 204
        assert not SimpleTransfer.objects.filter(pk=transfer_pk).exists()


class TestStayTransferViews:
    """Tests for StayTransfer CRUD views"""

    def test_create_stay_transfer_get(self, client, trip_factory, stay_factory):
        """Test GET request to create stay transfer form"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = stay_factory()
        stay2 = stay_factory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        client.force_login(trip.author)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_create_stay_transfer_post(self, client, trip_factory, stay_factory):
        """Test POST request to create stay transfer"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = stay_factory()
        stay2 = stay_factory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        client.force_login(trip.author)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert StayTransfer.objects.filter(from_stay=stay1).exists()

    def test_create_stay_transfer_no_next_day(self, client, trip_factory, stay_factory):
        """Test creating transfer when no next day exists"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay = stay_factory()
        days[2].stay = stay  # Last day
        days[2].save()

        client.force_login(trip.author)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[2].pk})
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert "HX-Trigger" in response.headers

    def test_create_stay_transfer_no_stays(self, client, trip_factory):
        """Test creating transfer when days have no stays"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())

        client.force_login(trip.author)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert "HX-Trigger" in response.headers

    def test_create_stay_transfer_same_stay(self, client, trip_factory, stay_factory):
        """Test creating transfer between same stay fails"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay = stay_factory()

        # Same stay on consecutive days
        days[0].stay = stay
        days[0].save()
        days[1].stay = stay
        days[1].save()

        client.force_login(trip.author)
        url = reverse("trips:create-stay-transfer", kwargs={"from_day_id": days[0].pk})
        response = client.post(url, {"transport_mode": "driving"})

        assert response.status_code == 204
        assert "HX-Trigger" in response.headers

    def test_edit_stay_transfer_get(self, client, trip_factory, stay_factory):
        """Test GET request to edit stay transfer form"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = stay_factory()
        stay2 = stay_factory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="driving"
        )

        client.force_login(trip.author)
        url = reverse("trips:edit-stay-transfer", kwargs={"pk": transfer.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_edit_stay_transfer_post(self, client, trip_factory, stay_factory):
        """Test POST request to edit stay transfer"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = stay_factory()
        stay2 = stay_factory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="driving"
        )

        client.force_login(trip.author)
        url = reverse("trips:edit-stay-transfer", kwargs={"pk": transfer.pk})
        response = client.post(url, {"transport_mode": "transit", "notes": "By train"})

        assert response.status_code == 204
        transfer.refresh_from_db()
        assert transfer.transport_mode == "transit"

    def test_delete_stay_transfer(self, client, trip_factory, stay_factory):
        """Test deleting a stay transfer"""
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = stay_factory()
        stay2 = stay_factory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="driving"
        )
        transfer_pk = transfer.pk

        client.force_login(trip.author)
        url = reverse("trips:delete-stay-transfer", kwargs={"pk": transfer.pk})
        response = client.post(url)

        assert response.status_code == 204
        assert not StayTransfer.objects.filter(pk=transfer_pk).exists()


class TestGetNextEventsForTransfer:
    """Tests for get_next_events_for_transfer HTMX view"""

    def test_get_next_events_no_from_event(
        self, client, trip_factory, experience_factory
    ):
        """Test getting all events when no from_event is selected"""
        trip = trip_factory()
        day = trip.days.first()
        experience_factory(trip=trip, day=day, start_time="10:00", end_time="11:00")
        experience_factory(trip=trip, day=day, start_time="14:00", end_time="15:00")

        client.force_login(trip.author)
        url = reverse("trips:get-next-events-for-transfer", kwargs={"day_id": day.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "events" in response.context
        assert len(response.context["events"]) == 2

    def test_get_next_events_with_from_event(
        self, client, trip_factory, experience_factory
    ):
        """Test getting only events after from_event"""
        trip = trip_factory()
        day = trip.days.first()
        event1 = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        experience_factory(trip=trip, day=day, start_time="14:00", end_time="15:00")

        client.force_login(trip.author)
        url = reverse("trips:get-next-events-for-transfer", kwargs={"day_id": day.pk})
        response = client.get(url, {"from_event": event1.pk})

        assert response.status_code == 200
        assert "events" in response.context
        # Should only return events after event1
        assert len(response.context["events"]) == 1


class TestEventChangeTimes:
    """Tests for event_change_times view"""

    def test_event_change_times_get(self, client, trip_factory, experience_factory):
        """Test GET request to change times form"""
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )

        client.force_login(trip.author)
        url = reverse("trips:event-change-times", kwargs={"pk": event.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_event_change_times_post(self, client, trip_factory, experience_factory):
        """Test POST request to change event times"""
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )

        client.force_login(trip.author)
        url = reverse("trips:event-change-times", kwargs={"pk": event.pk})
        response = client.post(url, {"start_time": "14:00", "end_time": "15:00"})

        assert response.status_code == 204
        event.refresh_from_db()
        assert str(event.start_time) == "14:00:00"
        assert str(event.end_time) == "15:00:00"
