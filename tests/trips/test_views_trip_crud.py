import datetime
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import Trip

pytestmark = pytest.mark.django_db


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

    def test_archive_resets_fav_trip_if_favourite(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        user.profile.fav_trip = trip
        user.profile.save()

        with self.login(user):
            response = self.post("trips:trip-archive", pk=trip.pk)

        self.response_204(response)
        user.profile.refresh_from_db()
        assert user.profile.fav_trip is None
        assert Trip.objects.filter(author=user, status=5).count() == 1

    def test_archive_does_not_reset_fav_trip_if_different(self):
        user = self.make_user("user")
        trip1 = TripFactory(author=user)
        trip2 = TripFactory(author=user)
        user.profile.fav_trip = trip1
        user.profile.save()

        with self.login(user):
            response = self.post("trips:trip-archive", pk=trip2.pk)

        self.response_204(response)
        user.profile.refresh_from_db()
        assert user.profile.fav_trip == trip1
        assert Trip.objects.filter(author=user, status=5).count() == 1


class TripUnarchiveView(TestCase):
    def test_unarchive(self):
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            status=5,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=5),
        )

        with self.login(user):
            response = self.post("trips:trip-unarchive", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> unarchived successfully"
        trip.refresh_from_db()
        assert trip.status == Trip.Status.COMPLETED


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
