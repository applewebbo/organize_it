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
