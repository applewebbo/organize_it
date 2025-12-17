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

    def test_avatar_widget_renders(self):
        """Test that avatar widget renders with images"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("accounts:profile")

        self.response_200()
        # Check that avatar choices are rendered with images
        content = response.content.decode()
        assert "hiker.png" in content
        assert "tourist.png" in content
        assert "/static/img/avatars/" in content
        assert "grid grid-cols-4 gap-4" in content

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

    def test_post_personal_information(self):
        """Test updating personal information fields"""
        user = self.make_user("user")
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "city": "Milan",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.city == "Milan"

    def test_post_avatar(self):
        """Test selecting avatar"""
        user = self.make_user("user")
        data = {"avatar": "hiker.png"}

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.avatar == "hiker.png"

    def test_post_all_fields(self):
        """Test updating all profile fields together"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "city": "Rome",
            "avatar": "tourist.png",
            "fav_trip": trip.pk,
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.first_name == "Jane"
        assert profile.last_name == "Smith"
        assert profile.city == "Rome"
        assert profile.avatar == "tourist.png"
        assert profile.fav_trip == trip
