import datetime
from unittest.mock import Mock, patch

import factory
import pytest
from django.contrib.messages import get_messages
from django.db.models import signals
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TransportFactory,
    TripFactory,
)
from trips.forms import ExperienceForm, MealForm, TransportForm
from trips.models import Stay, Trip

pytestmark = pytest.mark.django_db

mock_geocoder_response = Mock(latlng=(10.0, 20.0))
invalid_mock_geocoder_response = Mock(latlng=None)


@pytest.fixture
def mocked_geocoder():
    with patch(
        "trips.models.geocoder.mapbox", return_value=mock_geocoder_response
    ) as mocked_geocoder:
        yield mocked_geocoder


class HomeView(TestCase):
    def test_get(self):
        # Get the home view
        response = self.get("trips:home")
        # Check the status code and template used
        self.response_200(response)
        assertTemplateUsed(response, "trips/index.html")

    def test_get_with_authenticated_user(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert trip in response.context["other_trips"]

    def test_get_with_fav_trip(self):
        user = self.make_user("user")
        fav_trip = TripFactory(author=user)
        user.profile.fav_trip = fav_trip
        user.profile.save()

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["fav_trip"] == fav_trip

    @factory.django.mute_signals(signals.post_save)
    def test_get_with_no_profile(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)


class TripListView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-list.html")

    def test_trips(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        archived_trip = TripFactory(author=user, status=5)

        with self.login(user):
            response = self.get("trips:trip-list")

        assert trip in response.context["active_trips"]
        assert archived_trip in response.context["archived_trips"]

    def test_htmx_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-list", extra={"HTTP_HX-Request": "true"})

        self.response_200(response)
        assert "trips/trip-list.html" not in [t.name for t in response.templates]


class TripDetailView(TestCase):
    def test_get(self):
        """Test the trip detail view"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")

    def test_no_overlaps(self):
        """Test events with no overlaps"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create three events with non-overlapping times
        EventFactory(day=day, start_time="09:00", end_time="10:00")
        EventFactory(day=day, start_time="10:30", end_time="11:30")
        EventFactory(day=day, start_time="12:00", end_time="13:00")

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        events = response.context["trip"].days.first().events.all()

        # No events should have overlaps
        for event in events:
            assert not event.has_overlap

    def test_with_overlaps(self):
        """Test events with overlaps"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create three events with overlapping times
        EventFactory(day=day, start_time="09:00", end_time="10:00")
        EventFactory(day=day, start_time="09:30", end_time="10:30")
        EventFactory(day=day, start_time="10:00", end_time="11:00")

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        events = response.context["trip"].days.first().events.all()

        # All events should have overlaps
        for event in events:
            assert event.has_overlap


class TripCreateView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-create")

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-create.html")

    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "destination": "Novara",
            "description": "A trip to Paris",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_204(response)
        trip = Trip.objects.filter(author=user).first()
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> added successfully"
        assert Trip.objects.filter(author=user).count() == 1

    def test_post_with_invalid_start_date(self):
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "description": "A trip to Paris",
            "start_date": datetime.date.today() + datetime.timedelta(days=3),
            "end_date": datetime.date.today(),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_200(response)
        assert Trip.objects.filter(author=user).count() == 0


class TripDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.delete("trips:trip-delete", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> deleted successfully"
        assert Trip.objects.filter(author=user).count() == 0


class TripUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-update", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-create.html")

    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Paris",
            "destination": "Novara",
            "description": "A trip to Paris",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-update", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        trip = Trip.objects.filter(author=user).first()
        assert message == f"<strong>{trip.title}</strong> updated successfully"
        assert trip.title == data["title"]

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Paris",
        }

        with self.login(user):
            response = self.post("trips:trip-update", pk=trip.pk, data=data)

        self.response_200(response)


class TripArchiveView(TestCase):
    def test_archive(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.post("trips:trip-archive", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> archived successfully"
        assert Trip.objects.filter(author=user).count() == 1
        assert Trip.objects.filter(author=user, status=5).count() == 1


class TripDatesUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-dates", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-dates-update.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        trip = Trip.objects.filter(author=user).first()
        assert message == "Dates updated successfully"
        assert trip.start_date == data["start_date"]
        assert trip.end_date == data["end_date"]


class AddTransportView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "type": 1,
            "address": "Milan",
            "destination": "Rome",
            "start_time": "10:00",
            "end_time": "12:00",
            "url": "https://example.com",
        }

        with self.login(user):
            response = self.post("trips:add-transport", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Transport added successfully"
        assert day.events.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "type": 1,
        }

        with self.login(user):
            response = self.post("trips:add-transport", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/transport-create.html")
        assert day.events.count() == 0


class AddExperienceView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Walking Tour",
            "type": 1,
            "address": "Starting Point",
            "start_time": "14:00",
            "duration": "120",
            "url": "https://example.com",
        }

        with self.login(user):
            response = self.post("trips:add-experience", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Experience added successfully"
        assert day.events.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Visit Museum",
        }

        with self.login(user):
            response = self.post("trips:add-experience", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/experience-create.html")
        assert day.events.count() == 0


class AddMealView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "La Pergola",
            "type": 1,  # LUNCH
            "address": "Via Alberto Cadlolo, 101, Rome",
            "start_time": "13:00",
            "duration": "60",  # 1 hour
            "url": "https://example.com",
        }

        with self.login(user):
            response = self.post("trips:add-meal", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Meal added successfully"
        assert day.events.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Lunch",
        }

        with self.login(user):
            response = self.post("trips:add-meal", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/meal-create.html")
        assert day.events.count() == 0


class AddStayView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        day = days.first()
        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "url": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay added successfully"
        day.refresh_from_db()
        assert day.stay is not None

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Hotel",
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-create.html")
        assert day.stay is None

    @patch("geocoder.mapbox")
    def test_post_single_day(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        first_day = days.first()
        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "url": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [first_day.pk],  # Only apply to first day
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=first_day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay added successfully"

        # Refresh days from db and verify
        first_day.refresh_from_db()
        assert first_day.stay is not None

        # Other days should not have the stay
        other_days = days.exclude(pk=first_day.pk)
        for day in other_days:
            day.refresh_from_db()
            assert day.stay is None


class StayDetailView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        # Create stay and set days after creation
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-detail", pk=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-detail.html")
        assert response.context["stay"] == stay
        assert response.context["first_day"] == days.first()
        assert response.context["last_day"] == days.last()

    def test_get_with_previous_day(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.all())
        # Create stay and set only second day onwards
        stay = StayFactory()
        stay.days.set(days[1:])

        with self.login(user):
            response = self.get("trips:stay-detail", pk=stay.pk)

        self.response_200(response)
        assert (
            response.context["first_day"] == days[0]
        )  # Should be the day before first stay day
        assert response.context["last_day"] == days[-1]


class StayModifyView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        data = {
            "name": "Updated Hotel",
            "check_in": "15:00",
            "check_out": "10:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "url": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay updated successfully"
        stay.refresh_from_db()
        assert stay.name == "Updated Hotel"
        assert stay.check_in == datetime.time(15, 0)
        assert stay.check_out == datetime.time(10, 0)

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        data = {
            "name": "",  # Invalid: name is required
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-modify.html")


class StayDeleteView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-delete.html")
        assert response.context["stay"] == stay

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.post("trips:stay-delete", pk=stay.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay deleted successfully"
        assert not days.first().stay

    def test_get_with_single_other_stay(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])  # First two days
        other_stay.days.set(days[2:])  # Remaining days

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay.pk)

        self.response_200(response)
        assert response.context["show_dropdown"] is False
        assert response.context["other_stays"].count() == 1
        assert response.context["other_stays"].first() == other_stay

    def test_get_with_multiple_other_stays(self):
        """Test stay deletion view when there are multiple other stays available"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()

        # Create stays
        stay_to_delete = StayFactory()
        other_stay1 = StayFactory()
        other_stay2 = StayFactory()

        # Set days for each stay
        stay_to_delete.days.set(days[:2])
        other_stay1.days.set(days[2:4])
        other_stay2.days.set(days[4:])

        # Verify initial setup
        assert Stay.objects.count() == 3
        assert stay_to_delete.days.count() == 2
        assert other_stay1.days.count() == 2
        assert other_stay2.days.count() == len(days) - 4

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay_to_delete.pk)

        self.response_200(response)

        # Get other stays from response context
        other_stays = set(response.context["other_stays"])

        # Verify response context
        assert response.context["show_dropdown"] is True
        assert len(other_stays) == 2
        assert other_stays == {other_stay1, other_stay2}

    def test_post_with_single_other_stay_auto_reassign(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])
        other_stay.days.set(days[2:])

        with self.login(user):
            response = self.post("trips:stay-delete", pk=stay.pk)

        self.response_204(response)
        # Verify days were reassigned
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == other_stay

    def test_post_with_multiple_stays_manual_selection(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stays = [StayFactory(), StayFactory()]
        stay.days.set(days[:2])
        other_stays[0].days.set(days[2:4])
        other_stays[1].days.set(days[4:])

        with self.login(user):
            response = self.post(
                "trips:stay-delete", pk=stay.pk, data={"new_stay": other_stays[0].pk}
            )

        self.response_204(response)
        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == other_stays[0]

    def test_post_with_manual_stay_selection(self):
        """Test stay deletion when manually selecting a new stay from multiple options"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()

        # Create three stays
        stay_to_delete = StayFactory()
        new_stay = StayFactory()
        other_stay = StayFactory()

        # Assign days to stays
        stay_to_delete.days.set(days[:2])  # First two days
        new_stay.days.set(days[2:4])  # Next two days
        other_stay.days.set(days[4:])  # Remaining days

        # Verify initial setup
        assert Stay.objects.count() == 3

        with self.login(user):
            response = self.post(
                "trips:stay-delete",
                pk=stay_to_delete.pk,
                data={"new_stay": new_stay.pk},
            )

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay deleted successfully"

        # Verify stay was deleted
        assert not Stay.objects.filter(pk=stay_to_delete.pk).exists()

        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == new_stay


class EventDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.delete("trips:event-delete", pk=event.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event deleted successfully"
        assert event.day.events.count() == 0

    def test_delete_unauthorized(self):
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=other_user)
        event = EventFactory(trip=trip)

        with self.login(user):
            response = self.delete("trips:event-delete", pk=event.pk)

        self.response_404(response)
        assert event.day.events.count() == 1


class EventModifyView(TestCase):
    def test_get_transport(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = TransportFactory(day=day)  # Transport

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-modify.html")
        assert isinstance(response.context["form"], TransportForm)

    def test_get_experience(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(day=day)  # Experience

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_200(response)
        assert isinstance(response.context["form"], ExperienceForm)

    def test_get_meal(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = MealFactory(day=day)  # Meal

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_200(response)
        assert isinstance(response.context["form"], MealForm)

    def test_get_invalid_category(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        event = EventFactory(trip=trip, category=99)  # Invalid category

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_404(response)

    def test_get_unauthorized(self):
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=other_user)
        day = trip.days.first()
        event = ExperienceFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_404(response)

    @patch("geocoder.mapbox")
    def test_post_transport(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = TransportFactory(day=day)  # Transport
        data = {
            "address": "New Address",
            "destination": "New Destination",
            "start_time": "10:00",
            "end_time": "12:00",
            "url": "https://example.com",
            "type": 1,
        }

        with self.login(user):
            response = self.post("trips:event-modify", pk=event.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event updated successfully"
        event.refresh_from_db()
        assert event.name == "New Address - New Destination"

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = TransportFactory(day=day)  # Transport
        original_name = event.name
        data = {
            "name": "",  # Invalid: name is required
        }

        with self.login(user):
            response = self.post("trips:event-modify", pk=event.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-modify.html")
        event.refresh_from_db()
        assert event.name == original_name  # Check that name wasn't changed
