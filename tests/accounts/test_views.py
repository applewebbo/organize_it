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
        data = {
            "fav_trip": trip.pk,
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
        }

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
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
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
        data = {
            "avatar": "hiker.png",
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.avatar == "hiker.png"

    def test_post_currency(self):
        """Test updating currency preference"""
        user = self.make_user("user")
        data = {
            "currency": "USD",
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.currency == "USD"

    def test_post_default_map_view(self):
        """Test updating default map view preference"""
        user = self.make_user("user")
        data = {"default_map_view": "map", "trip_sort_preference": "date_asc"}

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.default_map_view == "map"

    def test_post_trip_sort_preference(self):
        """Test updating trip sort preference"""
        user = self.make_user("user")
        data = {
            "trip_sort_preference": "date_desc",
            "default_map_view": "list",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.trip_sort_preference == "date_desc"

    def test_post_use_system_theme(self):
        """Test enabling use system theme"""
        user = self.make_user("user")
        data = {
            "use_system_theme": True,
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.use_system_theme is True


class TestUpdateThemeView(TestCase):
    def test_update_theme_endpoint(self):
        """Test that update_theme endpoint exists and returns 204"""
        user = self.make_user("user")

        with self.login(user):
            response = self.post("accounts:update_theme", data={})

        self.assertEqual(response.status_code, 204)

    def test_update_theme_unauthenticated(self):
        """Test that unauthenticated users are redirected"""
        self.post("accounts:update_theme", data={})
        self.response_302()


class TestThemeSwitcherVisibility(TestCase):
    def test_theme_switcher_visible_when_not_using_system_theme(self):
        """Test that theme switcher is visible when use_system_theme is False"""
        user = self.make_user("user")
        user.profile.use_system_theme = False
        user.profile.save()

        with self.login(user):
            response = self.get("trips:home")

        self.response_200()
        content = response.content.decode()
        assert "theme-switcher.html" in content or "themeSwitcher" in content

    def test_theme_switcher_hidden_when_using_system_theme(self):
        """Test that theme switcher is hidden when use_system_theme is True"""
        user = self.make_user("user")
        user.profile.use_system_theme = True
        user.profile.save()

        with self.login(user):
            response = self.get("trips:home")

        self.response_200()
        content = response.content.decode()
        assert "themeSwitcher" not in content

    def test_theme_switcher_visible_for_unauthenticated_users(self):
        """Test that theme switcher is visible for unauthenticated users"""
        response = self.get("trips:home")

        self.response_200()
        content = response.content.decode()
        assert "themeSwitcher" in content


class TestProfileViewAllFields(TestCase):
    def test_post_all_fields(self):
        """Test updating all profile fields together"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "city": "Rome",
            "avatar": "tourist.png",
            "currency": "GBP",
            "default_map_view": "map",
            "trip_sort_preference": "name_asc",
            "use_system_theme": True,
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
        assert profile.currency == "GBP"
        assert profile.default_map_view == "map"
        assert profile.trip_sort_preference == "name_asc"
        assert profile.use_system_theme is True
        assert profile.fav_trip == trip
