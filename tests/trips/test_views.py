import factory
import pytest
from django.db.models import signals
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db


class TestHomeView(TestCase):
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


class TestTripListView(TestCase):
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
        # assertTemplateUsed(response, "trips/trip-list.html#trip-list")
        assert "trips/trip-list.html" not in [t.name for t in response.templates]
