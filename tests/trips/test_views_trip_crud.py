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

    @patch("geocoder.mapbox")
    def test_post_with_next_redirects_to_list(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "destination": "Novara",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.client.post(
                self.reverse("trips:trip-create") + "?next=list", data=data
            )

        self.response_204(response)
        assert response.headers.get("HX-Redirect") == self.reverse("trips:trip-list")

    def test_post_with_invalid_start_date(self):
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
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


class TripDestinationsView(TestCase):
    def test_get_modal(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/trip-destinations-modal.html")

    def test_get_modal_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)

        with self.login(other):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)

        self.response_404(response)


class UpdateDayDestinationView(TestCase):
    def test_post_updates_destination(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.post(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
                data={"destination": "Firenze"},
            )

        self.response_204(response)
        day.refresh_from_db()
        assert day.destination == "Firenze"

    def test_post_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        day = trip.days.first()

        with self.login(other):
            response = self.post(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
                data={"destination": "Firenze"},
            )

        self.response_404(response)

    def test_get_returns_card(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.get(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
            )

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/day-destination-card.html")
