import datetime
from unittest.mock import Mock, patch

import factory
import pytest
from django.contrib.messages import get_messages
from django.db.models import signals
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import Trip

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
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")

    # def test_map_bounds(self):
    #     user = self.make_user("user")
    #     trip = TripFactory(author=user)
    #     PlaceFactory.create_batch(2, trip=trip)

    #     with self.login(user):
    #         response = self.get("trips:trip-detail", pk=trip.pk)

    #     assert response.context["map_bounds"] is not None


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
