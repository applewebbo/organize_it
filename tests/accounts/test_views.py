# FILEPATH: /tests/test_views.py
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from accounts.models import Profile
from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.services import GooglePlacesError, PlaceResult

pytestmark = pytest.mark.django_db

MOCK_PLACES = [
    PlaceResult(
        place_id="ChIJ_test_001",
        name="Via Roma 1",
        address="Via Roma 1, Milano, Italy",
        lat=45.4654,
        lng=9.1859,
    ),
    PlaceResult(
        place_id="ChIJ_test_002",
        name="Via Verdi 5",
        address="Via Verdi 5, Torino, Italy",
        lat=45.0703,
        lng=7.6869,
    ),
]


class TestProfileView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("accounts:profile")
        # Check the status code and template used
        self.response_200()
        assert "account/profile.html" in [t.name for t in response.templates]

    def test_profile_does_not_duplicate_user_query(self):
        """The profile/settings page must not re-query the user (select_related)."""
        user = self.make_user("user")

        with self.login(user):
            with CaptureQueriesContext(connection) as ctx:
                response = self.get("accounts:profile")

        self.response_200(response)
        customuser_queries = sum(
            1 for q in ctx.captured_queries if 'FROM "accounts_customuser"' in q["sql"]
        )
        assert customuser_queries == 1, (
            f"expected 1 accounts_customuser query, got {customuser_queries}"
        )

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
            "language": "it",
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
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
            "language": "it",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"

    def test_post_avatar(self):
        """Test selecting avatar"""
        user = self.make_user("user")
        data = {
            "avatar": "hiker.png",
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
            "language": "it",
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
            "language": "it",
        }

        with self.login(user):
            response = self.post("accounts:profile", data=data)

        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.currency == "USD"

    def test_post_default_map_view(self):
        """Test updating default map view preference"""
        user = self.make_user("user")
        data = {
            "default_map_view": "map",
            "trip_sort_preference": "date_asc",
            "language": "it",
        }

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
            "language": "it",
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
            "language": "it",
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
            "avatar": "tourist.png",
            "currency": "GBP",
            "language": "en",
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
        assert profile.avatar == "tourist.png"
        assert profile.currency == "GBP"
        assert profile.default_map_view == "map"
        assert profile.trip_sort_preference == "name_asc"
        assert profile.use_system_theme is True
        assert profile.fav_trip == trip


class TestAutocompleteHomeAddressView(TestCase):
    def test_returns_results_for_valid_query(self):
        user = self.make_user("user")
        with self.login(user):
            with patch("accounts.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = MOCK_PLACES
                response = self.post(
                    "accounts:autocomplete-home-address",
                    data={"home_address": "Via Roma 1 Milano"},
                )
        self.response_200(response)
        assert response.context["found"] is True
        assert response.context["places"] == MOCK_PLACES

    def test_returns_not_found_for_empty_query(self):
        user = self.make_user("user")
        with self.login(user):
            response = self.post(
                "accounts:autocomplete-home-address",
                data={"home_address": ""},
            )
        self.response_200(response)
        assert response.context["found"] is False

    def test_returns_not_found_for_short_query(self):
        user = self.make_user("user")
        with self.login(user):
            response = self.post(
                "accounts:autocomplete-home-address",
                data={"home_address": "Vi"},
            )
        self.response_200(response)
        assert response.context["found"] is False

    def test_returns_not_found_on_api_error(self):
        user = self.make_user("user")
        with self.login(user):
            with patch("accounts.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.side_effect = GooglePlacesError(
                    "error"
                )
                response = self.post(
                    "accounts:autocomplete-home-address",
                    data={"home_address": "Via Roma 1 Milano"},
                )
        self.response_200(response)
        assert response.context["found"] is False

    def test_unauthenticated_redirects(self):
        self.post(
            "accounts:autocomplete-home-address", data={"home_address": "Via Roma"}
        )
        self.response_302()

    def test_get_not_allowed(self):
        user = self.make_user("user")
        with self.login(user):
            response = self.get("accounts:autocomplete-home-address")
        self.response_405(response)

    def test_returns_not_found_when_api_returns_empty_list(self):
        user = self.make_user("user")
        with self.login(user):
            with patch("accounts.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                response = self.post(
                    "accounts:autocomplete-home-address",
                    data={"home_address": "Indirizzo inesistente xyz"},
                )
        self.response_200(response)
        assert response.context["found"] is False


class TestProfileHomeAddressWithCoords(TestCase):
    def test_post_home_address_with_coordinates_skips_geocoding(self):
        """Coordinates from autocomplete are saved directly without triggering Mapbox fallback."""
        user = self.make_user("user")
        data = {
            "home_address": "Via Roma 1, Milano, Italy",
            "home_address_latitude": "45.4654",
            "home_address_longitude": "9.1859",
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
            "language": "it",
        }
        with self.login(user):
            with patch("accounts.models.geocoder") as mock_geocoder:
                response = self.post("accounts:profile", data=data)
                mock_geocoder.mapbox.assert_not_called()
        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.home_address == "Via Roma 1, Milano, Italy"
        assert profile.home_address_latitude == 45.4654
        assert profile.home_address_longitude == 9.1859

    def test_post_home_address_without_coordinates_triggers_fallback(self):
        """When no coordinates are provided, Mapbox fallback geocodes the address."""
        from unittest.mock import MagicMock

        user = self.make_user("user")
        mock_result = MagicMock()
        mock_result.latlng = [48.8566, 2.3522]
        data = {
            "home_address": "1 Rue de Rivoli, Paris",
            "trip_sort_preference": "date_asc",
            "default_map_view": "list",
            "language": "it",
        }
        with self.login(user):
            with patch("accounts.models.geocoder") as mock_geocoder:
                mock_geocoder.mapbox.return_value = mock_result
                response = self.post("accounts:profile", data=data)
        self.response_302(response)
        profile = Profile.objects.get(user=user)
        assert profile.home_address == "1 Rue de Rivoli, Paris"
        assert profile.home_address_latitude == 48.8566
        assert profile.home_address_longitude == 2.3522


class TestPrefilledPasswordReset(TestCase):
    def test_prefill_email_from_query_string(self):
        response = self.get("account_reset_password", data={"email": "foo@bar.com"})
        self.response_200(response)
        assert response.context["form"].initial.get("email") == "foo@bar.com"
        assert b'value="foo@bar.com"' in response.content

    def test_no_query_string_renders_empty(self):
        response = self.get("account_reset_password")
        self.response_200(response)
        assert "email" not in response.context["form"].initial
        assert b'value="foo@bar.com"' not in response.content

    def test_empty_query_string_renders_empty(self):
        response = self.get("account_reset_password", data={"email": "   "})
        self.response_200(response)
        assert "email" not in response.context["form"].initial

    def test_email_value_is_escaped(self):
        response = self.get(
            "account_reset_password", data={"email": '"><script>x</script>'}
        )
        self.response_200(response)
        assert b"<script>x</script>" not in response.content
