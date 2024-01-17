# FILEPATH: /tests/test_views.py
import pytest

from accounts.models import Profile
from tests.test import TestCase
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db


class TestProfileView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("accounts:profile")
        # Check the status code and template used
        self.response_200()
        assert "account/profile.html" in [t.name for t in response.templates]

    def test_unauthenticated_get(self):
        # Get the profile view
        self.get("accounts:profile")
        # Check the status code and redirect location
        self.response_302()

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {"fav_trip": trip.pk}

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        assert Profile.objects.get(user=user).fav_trip == trip

    def test_post_form_invalid(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {"fav_trip": trip}

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_200(response)
        assert response.context_data["profile_form"]
