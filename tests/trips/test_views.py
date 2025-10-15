import datetime
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
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
from trips.utils import generate_cache_key, geocode_location

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
        response = self.get("trips:home")
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

    def test_get_with_no_profile(self):
        user = self.make_user("user")
        user.profile.delete()

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
    """Test cases for trip detail view"""

    def test_get_trip_detail_success(self):
        """Test successful retrieval of trip detail page"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")
        assert response.context["trip"] == trip

    def test_get_trip_detail_not_found(self):
        """Test 404 response for non-existent trip"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-detail", pk=99999)

        self.response_404(response)

    def test_get_trip_detail_with_htmx(self):
        """Test that trip detail returns partial template with HTMX request"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get(
                "trips:trip-detail", pk=trip.pk, extra={"HTTP_HX-Request": "true"}
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/day.html")
        assert response.context["trip"] == trip

    def test_get_trip_detail_without_htmx(self):
        """Test that trip detail returns full template without HTMX request"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")
        assert response.context["trip"] == trip


class DayDetailView(TestCase):
    """Test cases for day detail view"""

    def test_get_day_detail_success(self):
        """Test successful retrieval of day detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/day.html")
        assert day.events.first() == event
        assert "day" in response.context
        assert response.context["day"] == day


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
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=3)
        data = {
            "start_date": start_date.strftime("%m/%d/%Y"),  # Format as MM/DD/YYYY
            "end_date": end_date.strftime("%m/%d/%Y"),  # Format as MM/DD/YYYY
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        trip = Trip.objects.filter(author=user).first()
        assert message == "Dates updated successfully"
        trip.refresh_from_db()
        assert trip.start_date == start_date
        assert trip.end_date == end_date

    def test_day_numbers_are_correct_and_unique_after_date_change(self):
        """
        Ensure that after changing the trip's start_date, all days have correct and unique numbers.
        """
        user = self.make_user("user")
        # Create a trip with 3 days
        start_date = datetime.date(2024, 5, 2)
        end_date = start_date + datetime.timedelta(days=2)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)
        days = list(trip.days.order_by("date"))
        assert [d.number for d in days] == [1, 2, 3]

        # Change start_date to add a day before
        trip.start_date = start_date - datetime.timedelta(days=1)
        trip.save()
        trip.refresh_from_db()
        days = list(trip.days.order_by("date"))

        # Check that numbers are 1, 2, 3, 4 and unique
        numbers = [d.number for d in days]
        assert numbers == [1, 2, 3, 4]
        assert len(numbers) == len(set(numbers)), "Day numbers are not unique"

        # Check that the dates are consecutive and ordered
        expected_dates = [
            trip.start_date + datetime.timedelta(days=i) for i in range(4)
        ]
        assert [d.date for d in days] == expected_dates


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
            "website": "https://example.com",
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
            "website": "https://example.com",
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
            "website": "https://example.com",
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
            "website": "https://example.com",
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
            "website": "https://example.com",
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
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_200(response)
        assert response.context["modified"]
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
        # Refresh the day from the database to get the updated stay value
        first_day = days.first()
        first_day.refresh_from_db()
        assert not first_day.stay

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

        # Create a trip with exactly 6 days
        start_date = datetime.date(2024, 1, 1)  # Use fixed date instead of today
        end_date = start_date + datetime.timedelta(days=5)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)

        # Get all days and ensure we have exactly 6
        days = list(trip.days.all().order_by("date"))
        assert len(days) == 6, f"Expected 6 days, got {len(days)}"

        # Create stays
        stay_to_delete = StayFactory()
        other_stay1 = StayFactory()
        other_stay2 = StayFactory()

        # Assign exactly 2 days to each stay
        stay_to_delete.days.set(days[:2])
        other_stay1.days.set(days[2:4])
        other_stay2.days.set(days[4:6])

        # Force refresh and verify setup
        for stay in [stay_to_delete, other_stay1, other_stay2]:
            stay.refresh_from_db()
            assert stay.days.count() == 2, f"Stay {stay.pk} should have exactly 2 days"

        # Verify trip has exactly 3 stays
        trip_stays = Stay.objects.filter(days__trip=trip).distinct()
        assert trip_stays.count() == 3, f"Expected 3 stays, got {trip_stays.count()}"

        # Get stay deletion page
        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay_to_delete.pk)

        self.response_200(response)

        # Verify response
        other_stays = response.context["other_stays"]
        assert other_stays.count() == 2, (
            f"Expected 2 other stays, got {other_stays.count()}"
        )
        assert set(other_stays) == {other_stay1, other_stay2}, "Wrong stays in context"
        assert response.context["show_dropdown"] is True, "show_dropdown should be True"

    def test_post_with_single_other_stay_auto_reassign(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])
        other_stay.days.set(days[2:])

        with self.login(user):
            response = self.post("trips:stay-delete", pk=other_stay.pk)

        self.response_204(response)
        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == stay

    def test_post_with_manual_stay_selection(self):
        """Test stay deletion when manually selecting a new stay from multiple options"""
        user = self.make_user("user")
        # Create a trip with exactly 6 days
        start_date = datetime.date(2024, 1, 1)  # Use fixed date instead of today
        end_date = start_date + datetime.timedelta(days=5)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)
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


class EventUnpairView(TestCase):
    def test_unpair(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.put("trips:event-unpair", pk=event.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event unpaired successfully"
        event.refresh_from_db()
        assert event.day is None


class EventPairView(TestCase):
    def test_pair(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)
        event.day = None  # Unpair the event first
        event.save()

        with self.login(user):
            response = self.put("trips:event-pair", pk=event.pk, day_id=day.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event paired successfully"
        event.refresh_from_db()
        assert event.day == day


class EventPairChoiceView(TestCase):
    """Test cases for event pair choice view"""

    def test_get_pair_choice(self):
        """Test successful retrieval of event pair choice page"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        event = EventFactory(trip=trip)
        event.day = None  # Ensure event is unpaired
        event.save()

        with self.login(user):
            response = self.get("trips:event-pair-choice", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-pair-choice.html")
        assert response.context["event"] == event
        assert list(response.context["days"]) == list(trip.days.all())

    def test_get_pair_choice_already_paired(self):
        """Test pair choice view with already paired event"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)  # Event is already paired

        with self.login(user):
            response = self.get("trips:event-pair-choice", pk=event.pk)

        self.response_200(response)
        assert list(response.context["days"]) == list(trip.days.all())


class EventModalView(TestCase):
    """Test cases for event modal view"""

    def test_get_modal(self):
        """Test successful retrieval of event modal"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-modal", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-modal.html")
        assert response.context["event"] == event


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
            "website": "https://example.com",
            "type": 1,
        }

        with self.login(user):
            response = self.post("trips:event-modify", pk=event.pk, data=data)

        self.response_200(response)
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


class TestEventOverlapCheck(TestCase):
    def test_overlap_warning(self):
        """Test that overlap warning is shown when times overlap"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create existing event
        EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(12, 0)
        )

        # Check overlap
        with self.login(user):
            response = self.get(
                "trips:check-event-overlap",
                day_id=day.pk,
                data={"start_time": "11:00", "end_time": "13:00"},
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/overlap-warning.html")
        assert "This event overlaps with another event" in str(response.content)

    def test_no_overlap_warning(self):
        """Test that no warning is shown when times don't overlap"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create existing event
        EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(12, 0)
        )

        # Check non-overlapping time
        with self.login(user):
            response = self.get(
                "trips:check-event-overlap",
                day_id=day.pk,
                data={"start_time": "13:00", "end_time": "14:00"},
            )

        self.response_200(response)
        assert response.content.decode() == ""

    def test_missing_time_parameters(self):
        """Test that empty response is returned when time parameters are missing"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        test_cases = [
            {},  # No parameters
            {"start_time": "10:00"},  # Only start_time
            {"end_time": "11:00"},  # Only end_time
            {"start_time": "", "end_time": ""},  # Empty parameters
        ]

        with self.login(user):
            for params in test_cases:
                response = self.get(
                    "trips:check-event-overlap", day_id=day.pk, data=params
                )
                self.response_200(response)
                assert response.content.decode() == ""


class TestEventSwap(TestCase):
    """Test cases for event swapping functionality"""

    def test_event_swap_success(self):
        """Test successful swapping of two events times"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        event1 = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )
        event2 = EventFactory(
            day=day, start_time=datetime.time(14, 0), end_time=datetime.time(15, 0)
        )

        with self.login(user):
            response = self.post("trips:event-swap", pk1=event1.pk, pk2=event2.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Events swapped successfully"

        # Verify events were swapped
        event1.refresh_from_db()
        event2.refresh_from_db()
        assert event1.start_time == datetime.time(14, 0)
        assert event1.end_time == datetime.time(15, 0)
        assert event2.start_time == datetime.time(10, 0)
        assert event2.end_time == datetime.time(11, 0)

    def test_event_swap_different_days(self):
        """Test swapping events from different days"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.first()
        day2 = trip.days.last()
        event1 = EventFactory(day=day1)
        event2 = EventFactory(day=day2)

        with self.login(user):
            response = self.post("trips:event-swap", pk1=event1.pk, pk2=event2.pk)

        self.response_400(response)


class TestEventSwapModal(TestCase):
    """Test cases for event swap modal view"""

    def test_get_swap_modal(self):
        """Test successful retrieval of swap modal"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        selected_event = EventFactory(day=day)
        swappable_event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-swap-modal", pk=selected_event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-swap.html")
        assert response.context["selected_event"] == selected_event
        assert swappable_event in response.context["swappable_events"]

    def test_get_swap_modal_no_other_events(self):
        """Test swap modal when no other events exist"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-swap-modal", pk=event.pk)

        self.response_200(response)
        assert len(response.context["swappable_events"]) == 0


class TestEventDetail(TestCase):
    """Test cases for event detail view"""

    def test_get_transport_detail(self):
        """Test successful retrieval of transport event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        transport = TransportFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=transport.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-detail.html")
        assert response.context["event"] == transport
        assert response.context["category"] == transport.category

    def test_get_experience_detail(self):
        """Test successful retrieval of experience event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        experience = ExperienceFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=experience.pk)

        self.response_200(response)
        assert response.context["event"] == experience
        assert response.context["category"] == experience.category

    def test_get_meal_detail(self):
        """Test successful retrieval of meal event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        meal = MealFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=meal.pk)

        self.response_200(response)
        assert response.context["event"] == meal
        assert response.context["category"] == meal.category

    def test_get_detail_unauthorized(self):
        """Test unauthorized access to event detail"""
        other_user = self.make_user("other")
        trip = TripFactory(author=other_user)
        day = trip.days.first()
        event = EventFactory(day=day)

        user = self.make_user("user")
        with self.login(user):
            response = self.get("trips:event-detail", pk=event.pk)

        self.response_404(response)

    def test_get_detail_invalid_category(self):
        """Test event detail with invalid category"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, category=99)  # Invalid category

        with self.login(user):
            response = self.get("trips:event-detail", pk=event.pk)

        self.response_404(response)


class TestEventChangeTimes(TestCase):
    """Test cases for event time changes"""

    def test_get_change_times(self):
        """Test successful retrieval of change times form"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )

        with self.login(user):
            response = self.get("trips:event-change-times", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-change-times.html")
        assert "form" in response.context
        assert response.context["event"] == event

    def test_post_change_times_success(self):
        """Test successful time update"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )

        data = {
            "start_time": "14:00",
            "end_time": "15:00",
        }

        with self.login(user):
            response = self.post("trips:event-change-times", pk=event.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event times updated successfully"

        event.refresh_from_db()
        assert event.start_time == datetime.time(14, 0)
        assert event.end_time == datetime.time(15, 0)

    def test_post_change_times_invalid(self):
        """Test time update with invalid data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )

        data = {
            "start_time": "",  # Invalid: required field
            "end_time": "15:00",
        }

        with self.login(user):
            response = self.post("trips:event-change-times", pk=event.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-change-times.html")
        assert "form" in response.context
        assert response.context["form"].errors

        event.refresh_from_db()
        assert event.start_time == datetime.time(10, 0)  # Time shouldn't change

    def test_get_change_times_unauthorized(self):
        """Test unauthorized access to change times"""
        other_user = self.make_user("other")
        trip = TripFactory(author=other_user)
        day = trip.days.first()
        event = EventFactory(day=day)

        user = self.make_user("user")
        with self.login(user):
            response = self.get("trips:event-change-times", pk=event.pk)

        self.response_404(response)


class TestViewLogFile(TestCase):
    """
    Tests for the view_log_file function-based view.
    """

    def test_view_log_file_success(self):
        """
        Should return the content of the log file if it exists and user is staff.
        """
        log_content = "test log content"
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_file_path = f"{tmpdirname}/test.log"
            with open(log_file_path, "w") as f:
                f.write(log_content)
            url = reverse("trips:log", kwargs={"filename": "test.log"})
            user = self.make_user()
            user.is_staff = True
            user.save()
            with self.login(user), override_settings(BASE_DIR=Path(tmpdirname)):
                response = self.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert log_content in response.content.decode()

    def test_view_log_file_not_found(self):
        """
        Should return 404 if the log file does not exist and user is staff.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            url = reverse("trips:log", kwargs={"filename": "notfound.log"})
            user = self.make_user()
            user.is_staff = True
            user.save()
            with self.login(user), override_settings(BASE_DIR=Path(tmpdirname)):
                response = self.get(url)

        assert response.status_code == 404

    def test_view_log_file_forbidden_for_non_staff(self):
        """
        Should return 302 redirect to login for non-staff users.
        """
        log_content = "test log content"
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_file_path = f"{tmpdirname}/test.log"
            with open(log_file_path, "w") as f:
                f.write(log_content)
            url = reverse("trips:log", kwargs={"filename": "test.log"})
            user = self.make_user()
            user.is_staff = False
            user.save()
            with self.login(user), override_settings(BASE_DIR=Path(tmpdirname)):
                response = self.get(url)

        assert response.status_code == 302


class ValidateDatesViewTests(TestCase):
    """
    Tests for the validate_dates function-based view.
    """

    def test_valid_dates(self):
        """Should return empty response if dates are valid."""
        today = datetime.date.today()
        data = {
            "start_date": today.isoformat(),
            "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_start_date_before_today(self):
        """Should return error if start_date is before today."""
        today = datetime.date.today()
        data = {
            "start_date": (today - datetime.timedelta(days=1)).isoformat(),
            "end_date": today.isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert b"Start date must be after today" in response.content

    def test_start_date_after_end_date(self):
        """Should return error if start_date is after end_date."""
        today = datetime.date.today()
        data = {
            "start_date": (today + datetime.timedelta(days=2)).isoformat(),
            "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert b"Start date cannot be after end date" in response.content

    def test_invalid_date_format(self):
        """Should return empty response if date format is invalid."""
        data = {
            "start_date": "not-a-date",
            "end_date": "also-not-a-date",
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_both_errors(self):
        """Should return both errors if start_date is before today and after end_date."""
        today = datetime.date.today()
        data = {
            "start_date": (today - datetime.timedelta(days=1)).isoformat(),
            "end_date": (today - datetime.timedelta(days=2)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert b"Start date must be after today" in response.content
        assert b"Start date cannot be after end date" in response.content

    def test_missing_start_date(self):
        """Should return empty response if start_date is missing."""
        today = datetime.date.today()
        data = {
            "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_missing_end_date(self):
        """Should return empty response if end_date is missing."""
        today = datetime.date.today()
        data = {
            "start_date": today.isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_missing_both_dates(self):
        """Should return empty response if both start_date and end_date are missing."""
        data = {}
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""


class EventNotesView(TestCase):
    def test_event_notes_with_note(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Test note content")

        with self.login(user):
            response = self.get("trips:event-notes", event_id=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-notes.html")
        assert response.context["event"] == event
        assert response.context["form"].instance == event
        assert response.context["form"].initial["notes"] == "Test note content"

    def test_event_notes_without_note(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="")

        with self.login(user):
            response = self.get("trips:event-notes", event_id=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-notes.html")
        assert response.context["event"] == event
        assert response.context["form"].instance == event
        assert response.context["form"].initial["notes"] == ""


class StayNotesView(TestCase):
    def test_stay_notes_with_note(self):
        """
        Test stay_notes view when the stay has a note.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Test stay note")
        stay.save()  # Ensure stay has a primary key
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-notes", stay_id=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-notes.html")
        assert response.context["stay"] == stay
        assert response.context["form"].instance == stay
        assert response.context["form"].initial["notes"] == "Test stay note"

    def test_stay_notes_without_note(self):
        """
        Test stay_notes view when the stay has no note.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="")
        stay.save()  # Ensure stay has a primary key
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-notes", stay_id=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-notes.html")
        assert response.context["stay"] == stay
        assert response.context["form"].instance == stay
        assert response.context["form"].initial["notes"] == ""


class NoteCreateView(TestCase):
    def test_note_create_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="")
        data = {"notes": "This is a test note."}

        with self.login(user):
            response = self.post("trips:note-create", event_id=event.pk, data=data)

        self.response_204(response)
        event.refresh_from_db()
        assert event.notes == data["notes"]

    def test_note_create_invalid_data(self):
        """
        Test note creation with invalid data: send a value that is too long for the notes field.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="")
        data = {"notes": ""}

        with self.login(user):
            response = self.post("trips:note-create", event_id=event.pk, data=data)

        assert response.status_code == 400
        event.refresh_from_db()
        assert event.notes == ""


class NoteModifyView(TestCase):
    def test_note_modify_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Old note")
        data = {"notes": "Updated note content"}

        with self.login(user):
            response = self.post("trips:note-modify", event_id=event.pk, data=data)

        self.response_200(response)
        event.refresh_from_db()
        assert event.notes == data["notes"]

    def test_note_modify_invalid_data(self):
        """
        Test modifying an event's note with invalid data (empty string).
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Some note")
        data = {"notes": ""}  # Notes can be blank

        with self.login(user):
            response = self.post("trips:note-modify", event_id=event.pk, data=data)

        self.response_200(response)
        event.refresh_from_db()
        assert event.notes == "Some note"


class NoteDeleteView(TestCase):
    def test_note_delete_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Some note")

        with self.login(user):
            response = self.post("trips:note-delete", event_id=event.pk)

        self.response_204(response)
        event.refresh_from_db()
        assert event.notes == ""


class StayNoteCreateView(TestCase):
    def test_stay_note_create_success(self):
        """
        Test successful creation of a note for a stay.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="")
        stay.save()
        stay.days.set(days)
        data = {"notes": "This is a test stay note."}

        with self.login(user):
            response = self.post("trips:stay-note-create", stay_id=stay.pk, data=data)

        self.response_204(response)
        stay.refresh_from_db()
        assert stay.notes == data["notes"]

    def test_stay_note_create_invalid_data(self):
        """
        Test stay note creation with invalid data: send a value that is too long for the notes field.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="")
        stay.save()
        stay.days.set(days)
        # Assuming notes field has max_length=500
        data = {"notes": "a" * 1001}  # Exceeds max_length

        with self.login(user):
            response = self.post("trips:stay-note-create", stay_id=stay.pk, data=data)

        assert response.status_code == 400
        stay.refresh_from_db()
        assert stay.notes == ""


class StayNoteModifyView(TestCase):
    def test_stay_note_modify_success(self):
        """
        Test successful modification of a note for a stay.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Original stay note")
        stay.save()
        stay.days.set(days)
        data = {"notes": "Updated stay note content."}

        with self.login(user):
            response = self.post("trips:stay-note-modify", stay_id=stay.pk, data=data)

        self.response_200(response)
        stay.refresh_from_db()
        assert stay.notes == data["notes"]

    def test_stay_note_modify_invalid_data(self):
        """
        Test modification of a stay note with invalid data: send a value that is too long for the notes field.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Original stay note")
        stay.save()
        stay.days.set(days)
        # Assuming notes field has max_length=500
        data = {"notes": "a" * 1001}  # Exceeds max_length

        with self.login(user):
            response = self.post("trips:stay-note-modify", stay_id=stay.pk, data=data)

        assert response.status_code == 200  # Form should be invalid and re-rendered
        stay.refresh_from_db()
        assert stay.notes == "Original stay note"


class StayNoteDeleteView(TestCase):
    def test_stay_note_delete_success(self):
        """
        Test successful deletion of a note for a stay.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Note to delete")
        stay.save()
        stay.days.set(days)

        with self.login(user):
            response = self.post("trips:stay-note-delete", stay_id=stay.pk)

        self.response_204(response)
        stay.refresh_from_db()
        assert stay.notes == ""

    def test_stay_note_delete_not_found(self):
        """
        Test deletion of a note for a non-existent stay returns 404.
        """
        user = self.make_user("user")
        with self.login(user):
            response = self.post("trips:stay-note-delete", stay_id=99999)
        self.response_404(response)


class RateLimitCheckTests(TestCase):
    def test_rate_limit_check_waits_if_called_too_soon(self):
        """Should sleep if called within 1 second of last request."""

        from trips.utils import rate_limit_check

        cache.set("nominatim_last_request_time", time.time(), 60)
        start = time.time()
        rate_limit_check()
        elapsed = time.time() - start
        assert elapsed >= 0.99  # Should wait at least ~1 second

    def test_rate_limit_check_no_wait_if_enough_time_passed(self):
        """Should not sleep if more than 1 second has passed since last request."""

        from trips.utils import rate_limit_check

        cache.set("nominatim_last_request_time", time.time() - 2, 60)
        start = time.time()
        rate_limit_check()
        elapsed = time.time() - start
        assert elapsed < 0.5  # Should not wait


class GenerateCacheKeyTests(TestCase):
    def test_generate_cache_key_basic(self):
        key = generate_cache_key("Hotel Milano", "Milan")
        assert key.startswith("geocode_")
        assert len(key) < 100  # Should not be excessively long

    def test_generate_cache_key_empty(self):
        key = generate_cache_key("", "")
        assert key.startswith("geocode_")
        assert len(key) < 100  # Should not be excessively long


class GeocodeLocationTests(TestCase):
    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_sorted_addresses(self, mock_get):
        from trips.utils import geocode_location

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "address": {"road": "Via Roma", "city": "Rome"},
                "lat": "41.9028",
                "lon": "12.4964",
                "importance": 0.7,
                "place_rank": 30,
                "name": "Hotel Roma",
            },
            {
                "address": {"road": "Via Milano", "city": "Milan"},
                "lat": "45.4642",
                "lon": "9.19",
                "importance": 0.9,
                "place_rank": 30,
                "name": "Hotel Milano",
            },
        ]
        addresses = geocode_location("Hotel", "Italy")
        assert len(addresses) == 2
        # Should be sorted by importance descending
        assert addresses[0]["address"].endswith("Milan")
        assert addresses[1]["address"].endswith("Rome")

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_empty_on_no_results(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}
        addresses = geocode_location("Nonexistent", "Nowhere")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("API error")
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_empty_list_response(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []  # Simulate API returns empty list
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_non_200_status_code(self, mock_get):
        """Should return [] if API response status code is not 200."""
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = [
            {
                "address": {"road": "Via Roma", "city": "Rome"},
                "lat": "41.9028",
                "lon": "12.4964",
                "importance": 0.7,
                "place_rank": 30,
                "name": "Hotel Roma",
            }
        ]
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    def test_geocode_location_returns_none_if_name_or_city_missing(self):
        assert geocode_location("", "Rome") is None
        assert geocode_location("Hotel", "") is None

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_cached_result(self, mock_get):
        # Prepare a fake cached result
        cached_result = [
            {
                "address": "Via Roma 1, Rome",
                "lat": 41.9028,
                "lon": 12.4964,
                "importance": 0.7,
                "place_rank": 30,
            }
        ]
        key = generate_cache_key("Hotel Roma", "Rome")
        cache.set(key, cached_result, 60)
        # Should return cached result and not call requests.get
        addresses = geocode_location("Hotel Roma", "Rome")
        assert addresses == cached_result
        assert not mock_get.called


class GeocodeLocationAddressFormatTests(TestCase):
    def test_address_format_with_only_street_and_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"road": "Via Milano", "city": "Milan"},
                    "lat": "45.4642",
                    "lon": "9.19",
                    "importance": 0.9,
                    "place_rank": 30,
                    "name": "Hotel Milano",
                }
            ]
            addresses = geocode_location("Hotel Milano", "Milan")
            assert addresses[0]["address"] == "Via Milano, Milan"

    def test_address_format_with_street_housenumber_and_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {
                        "road": "Via Roma",
                        "house_number": "1",
                        "city": "Rome",
                    },
                    "lat": "41.9028",
                    "lon": "12.4964",
                    "importance": 0.7,
                    "place_rank": 30,
                    "name": "Hotel Roma",
                }
            ]
            addresses = geocode_location("Hotel Roma", "Rome")
            assert addresses[0]["address"] == "Via Roma 1, Rome"

    def test_address_format_with_only_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"city": "Naples"},
                    "lat": "40.8522",
                    "lon": "14.2681",
                    "importance": 0.5,
                    "place_rank": 30,
                    "name": "Napoli",
                }
            ]
            addresses = geocode_location("Napoli", "Naples")
            assert addresses[0]["address"] == "Naples"

    def test_address_format_with_street_housenumber_no_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"road": "Via Firenze", "house_number": "22"},
                    "lat": "43.7696",
                    "lon": "11.2558",
                    "importance": 0.6,
                    "place_rank": 30,
                    "name": "Hotel Firenze",
                }
            ]
            addresses = geocode_location("Hotel Firenze", "Firenze")
            assert addresses[0]["address"] == "Via Firenze 22"


class SelectBestResultTests(TestCase):
    def test_select_best_result_returns_none_for_empty(self):
        from trips.utils import select_best_result

        assert select_best_result([], "Hotel", "Rome") is None

    def test_select_best_result_prefers_city_and_name(self):
        from trips.utils import select_best_result

        results = [
            {
                "display_name": "Hotel Roma, Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.5,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
            {
                "display_name": "Hotel Milano, Milan, Italy",
                "address": {"city": "Milan"},
                "importance": 0.9,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
        ]
        best = select_best_result(results, "Hotel Roma", "Rome")
        assert best["address"]["city"] == "Rome"

    def test_select_best_result_penalizes_generic_place(self):
        from trips.utils import select_best_result

        results = [
            {
                "display_name": "Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.8,
                "place_rank": 20,
                "class": "place",
                "type": "city",
            },
            {
                "display_name": "Hotel Roma, Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.5,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
        ]
        best = select_best_result(results, "Hotel Roma", "Rome")
        assert best["class"] == "tourism"
        assert best["type"] == "hotel"

    def test_select_best_result_returns_first_if_no_scores(self):
        from trips.utils import select_best_result

        results = [
            {"display_name": "A", "address": {}, "importance": 0.1, "place_rank": 99},
            {"display_name": "B", "address": {}, "importance": 0.1, "place_rank": 99},
        ]
        best = select_best_result(results, "", "")
        assert best == results[0]


class GeocodeAddressViewTests(TestCase):
    @patch("trips.views.geocode_location")
    def test_geocode_address_post_found(self, mock_geocode_location):
        from django.urls import reverse

        mock_geocode_location.return_value = [
            {
                "name": "Hotel Roma",
                "address": "Via Roma 1, Rome",
                "lat": 41.9,
                "lon": 12.5,
                "importance": 0.9,
                "place_rank": 30,
            }
        ]
        response = self.client.post(
            reverse("trips:geocode-address"), {"name": "Hotel Roma", "city": "Rome"}
        )
        assert response.status_code == 200
        assert b"Hotel Roma" in response.content
        assert b"Via Roma 1, Rome" in response.content

    @patch("trips.views.geocode_location")
    def test_geocode_address_post_not_found(self, mock_geocode_location):
        from django.urls import reverse

        mock_geocode_location.return_value = []
        response = self.client.post(
            reverse("trips:geocode-address"), {"name": "Hotel Roma", "city": "Rome"}
        )
        assert response.status_code == 200
        assert (
            b"No address found" in response.content or b"found" not in response.content
        )

    def test_geocode_address_post_missing_fields(self):
        from django.urls import reverse

        response = self.client.post(
            reverse("trips:geocode-address"), {"name": "", "city": "Rome"}
        )
        assert response.status_code == 200
        assert (
            b"No address found" in response.content or b"found" not in response.content
        )

    def test_geocode_address_get(self):
        from django.urls import reverse

        response = self.client.get(reverse("trips:geocode-address"))
        assert response.status_code == 200
        assert (
            b"No address found" in response.content or b"found" not in response.content
        )


class DayMapViewTests(TestCase):
    """Test cases for DayMapView"""

    def test_get_day_map_view_success(self):
        """Test successful retrieval of day map view"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(latitude=45.4642, longitude=9.1900)
        day.stay = stay
        day.save()
        EventFactory(name="Event 1", day=day, latitude=45.4642, longitude=9.1900)
        EventFactory(name="Event 2", day=day, latitude=45.4652, longitude=9.1910)

        with self.login(user):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/day-map.html")
        assert response.context["day"] == day
        assert "map" in response.context
        assert response.context["map"] is not None
        assert "folium-map" in response.context["map"]

    def test_get_day_map_view_with_next_day_stay(self):
        """Test day map view with a different stay on the next day."""
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day1, day2 = trip.days.all()
        stay1 = StayFactory()
        stay2 = StayFactory()
        day1.stay = stay1
        day1.save()
        day2.stay = stay2
        day2.save()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day1.pk)

        self.response_200(response)
        assert response.context["locations"]["next_day_stay"] == stay2

    def test_get_day_map_view_first_day(self):
        """Test day map view for the first day of a stay."""
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day1, day2 = trip.days.all()
        stay = StayFactory()
        day2.stay = stay
        day2.save()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day2.pk)

        self.response_200(response)
        assert response.context["locations"]["first_day"] is True

    def test_get_day_map_view_not_first_day(self):
        """Test day map view for a day that is not the first day of a stay."""
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day1, day2 = trip.days.all()
        stay = StayFactory()
        day1.stay = stay
        day1.save()
        day2.stay = stay
        day2.save()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day2.pk)

        self.response_200(response)
        assert "first_day" not in response.context["locations"]

    def test_get_day_map_view_no_events(self):
        """Test day map view with no events"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/day-map.html")
        assert response.context["day"] == day
        assert response.context["map"] is None

    def test_get_day_map_view_events_no_location(self):
        """Test day map view with events that have no location"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        EventFactory(day=day, latitude=None, longitude=None)

        with self.login(user):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/day-map.html")
        assert response.context["day"] == day

    def test_get_day_map_view_not_found(self):
        """Test 404 response for non-existent day"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:day-map", day_id=99999)

        self.response_404(response)

    def test_get_day_map_view_unauthenticated(self):
        """Test that unauthenticated users are redirected to login"""
        trip = TripFactory()
        day = trip.days.first()
        response = self.get("trips:day-map", day_id=day.pk)
        self.response_302(response)
        assert "/login/" in response.url

    def test_get_day_map_view_unauthorized(self):
        """Test that users cannot access other users' day maps"""
        user1 = self.make_user("user1")
        trip = TripFactory(author=user1)
        day = trip.days.first()

        user2 = self.make_user("user2")
        with self.login(user2):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_404(response)


class SingleEventViewTest(TestCase):
    """Test cases for single_event view"""

    def test_get_single_event_success(self):
        """Test successful retrieval of a single event"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip)

        with self.login(user):
            response = self.get("trips:single-event", pk=event.pk)

        self.response_200(response)
        self.assertContains(response, event.name)
        assert response.context["event"] == event


@patch("trips.views.requests.get")
@patch("trips.views.requests.post")
class EnrichEventViewTest(TestCase):
    """Test cases for enrich_event view"""

    def test_enrich_event_success(self, mock_post, mock_get):
        """Test successful enrichment of an event"""
        # Mock Google Places API responses
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            "regularOpeningHours": {
                "periods": [
                    {
                        "open": {"day": 1, "hour": 9, "minute": 0},
                        "close": {"day": 1, "hour": 17, "minute": 0},
                    }
                ]
            },
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_204(response)
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.website == "https://example.com"
        assert event.phone_number == "+1234567890"
        assert "monday" in event.opening_hours
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == "Event enriched successfully!"

    def test_enrich_event_no_name_or_address(self, mock_post, mock_get):
        """Test enrichment with no name or address"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, name="", address="")

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 400
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert (
            str(messages[0]) == "Event must have a name and an address to be enriched."
        )

    def test_enrich_event_no_api_key(self, mock_post, mock_get):
        """Test enrichment with no API key"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY=""):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 500
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == "Google Places API key is not configured."

    def test_enrich_event_search_request_fails(self, mock_post, mock_get):
        """Test enrichment when search request fails"""
        mock_post.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 500
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "Error calling Google Places API: Test error" in str(messages[0])

    def test_enrich_event_search_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when search request fails with a response"""
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_post.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 500
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "API Error: API error details" in str(messages[0])

    def test_enrich_event_no_place_found(self, mock_post, mock_get):
        """Test enrichment when no place is found"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": []}

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 404
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert str(messages[0]) == "Could not find a matching place."

    def test_enrich_event_details_request_fails(self, mock_post, mock_get):
        """Test enrichment when details request fails"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 500
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "Error calling Google Places API: Test error" in str(messages[0])

    def test_enrich_event_details_request_fails_with_response(
        self, mock_post, mock_get
    ):
        """Test enrichment when details request fails with a response"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_get.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        assert response.status_code == 500
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "API Error: API error details" in str(messages[0])
