from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


class TestCustomUser:
    def test_create_user(self, user_factory):
        """Test creating a new user"""
        user = user_factory()

        assert user.__str__() == user.email

    def test_automatic_profile_creation(self, user_factory):
        """Test automatic profile creation"""
        user = user_factory()

        assert hasattr(user, "profile")
        assert user.profile.__str__() == user.email
        assert user.profile.fav_trip is None


class TestProfile:
    def test_new_fields_default_values(self, user_factory):
        """Test that new profile fields have correct default values"""
        user = user_factory()
        profile = user.profile

        assert profile.first_name == ""
        assert profile.last_name == ""
        assert profile.city == ""
        assert profile.avatar == ""
        assert profile.currency == "EUR"
        assert profile.default_map_view == "list"

    def test_update_personal_information(self, user_factory):
        """Test updating profile personal information fields"""
        user = user_factory()
        profile = user.profile

        profile.first_name = "John"
        profile.last_name = "Doe"
        profile.city = "Milan"
        profile.avatar = "hiker.png"
        profile.save()

        profile.refresh_from_db()
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.city == "Milan"
        assert profile.avatar == "hiker.png"

    def test_currency_field_choices(self, user_factory):
        """Test that currency field accepts valid choices"""
        user = user_factory()
        profile = user.profile

        # Test EUR (default)
        assert profile.currency == "EUR"

        # Test USD
        profile.currency = "USD"
        profile.save()
        profile.refresh_from_db()
        assert profile.currency == "USD"

        # Test GBP
        profile.currency = "GBP"
        profile.save()
        profile.refresh_from_db()
        assert profile.currency == "GBP"

    def test_default_map_view_field_choices(self, user_factory):
        """Test that default_map_view field accepts valid choices"""
        user = user_factory()
        profile = user.profile

        # Test list (default)
        assert profile.default_map_view == "list"

        # Test map
        profile.default_map_view = "map"
        profile.save()
        profile.refresh_from_db()
        assert profile.default_map_view == "map"

    def test_trip_sort_preference_default_value(self, user_factory):
        """Test that trip_sort_preference has correct default value"""
        user = user_factory()
        profile = user.profile

        assert profile.trip_sort_preference == "date_asc"

    def test_trip_sort_preference_field_choices(self, user_factory):
        """Test that trip_sort_preference field accepts valid choices"""
        user = user_factory()
        profile = user.profile

        # Test date_asc (default)
        assert profile.trip_sort_preference == "date_asc"

        # Test date_desc
        profile.trip_sort_preference = "date_desc"
        profile.save()
        profile.refresh_from_db()
        assert profile.trip_sort_preference == "date_desc"

        # Test name_asc
        profile.trip_sort_preference = "name_asc"
        profile.save()
        profile.refresh_from_db()
        assert profile.trip_sort_preference == "name_asc"

        # Test name_desc
        profile.trip_sort_preference = "name_desc"
        profile.save()
        profile.refresh_from_db()
        assert profile.trip_sort_preference == "name_desc"

    def test_home_address_default_empty(self, user_factory):
        """Test that home_address defaults to empty string"""
        user = user_factory()
        assert user.profile.home_address == ""
        assert user.profile.home_address_latitude is None
        assert user.profile.home_address_longitude is None

    def test_home_address_can_be_saved(self, user_factory):
        """Test saving home_address persists correctly"""
        user = user_factory()
        profile = user.profile
        profile.home_address = "Via Roma 1, Milano, Italia"
        profile.home_address_latitude = 45.464664
        profile.home_address_longitude = 9.188540
        profile.save()
        profile.refresh_from_db()
        assert profile.home_address == "Via Roma 1, Milano, Italia"
        assert profile.home_address_latitude == 45.464664
        assert profile.home_address_longitude == 9.188540

    def test_geocoding_skipped_when_address_unchanged(self, user_factory):
        """Geocoding is skipped when home_address is the same as before and no coords"""
        from accounts.models import Profile

        user = user_factory()
        # Set address directly via update() so save() is not called and no coords are set
        Profile.objects.filter(pk=user.profile.pk).update(
            home_address="Via Roma 1, Milano"
        )
        user.profile.refresh_from_db()

        with patch("accounts.models.geocoder") as mock_geocoder:
            # Save with same address: address_changed=False → geocoder NOT called
            user.profile.save()

        mock_geocoder.mapbox.assert_not_called()

    def test_geocoding_skipped_when_latlng_empty(self, user_factory):
        """Geocoding failure (empty latlng) does not raise and coords stay None"""
        user = user_factory()
        profile = user.profile

        mock_result = MagicMock()
        mock_result.latlng = None

        with patch("accounts.models.geocoder") as mock_geocoder:
            mock_geocoder.mapbox.return_value = mock_result
            profile.home_address = "Indirizzo Inesistente XYZ 999"
            profile.save()

        profile.refresh_from_db()
        assert profile.home_address_latitude is None
        assert profile.home_address_longitude is None
