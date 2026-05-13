from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

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


class TestGetProfile:
    def test_returns_profile(self, user_factory):
        from accounts.models import get_profile

        user = user_factory()
        profile = get_profile(user)
        assert profile.user == user

    def test_cache_hit(self, user_factory):
        """Second call returns cached profile without hitting DB."""
        from accounts.models import get_profile

        user = user_factory()
        profile_first = get_profile(user)
        profile_second = get_profile(user)
        assert profile_first.pk == profile_second.pk


class TestProfile:
    def test_new_fields_default_values(self, user_factory):
        """Test that new profile fields have correct default values"""
        user = user_factory()
        profile = user.profile

        assert profile.first_name == ""
        assert profile.last_name == ""
        assert profile.avatar == ""
        assert profile.currency == "EUR"
        assert profile.default_map_view == "list"

    def test_update_personal_information(self, user_factory):
        """Test updating profile personal information fields"""
        user = user_factory()
        profile = user.profile

        profile.first_name = "John"
        profile.last_name = "Doe"
        profile.avatar = "hiker.png"
        profile.save()

        profile.refresh_from_db()
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
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

    def test_save_invalidates_cache(self, user_factory):
        """Profile.save() must invalidate the profile cache."""
        from accounts.models import get_profile

        user = user_factory()
        cache_key = f"profile_{user.pk}"
        get_profile(user)  # populate cache
        assert cache.get(cache_key) is not None
        user.profile.save()
        assert cache.get(cache_key) is None

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


class TestProfileHomeAddressSignal:
    @patch("accounts.models.async_task")
    def test_triggers_recalculation_when_home_coords_change(
        self, mock_async, user_factory, trip_factory
    ):
        """When home coords change, recalculate first/last day for active trips."""
        from accounts.models import Profile

        user = user_factory()
        today = date.today()
        trip = trip_factory(
            author=user,
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=10),
        )
        days = list(trip.days.order_by("number"))
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        profile = user.profile
        profile.refresh_from_db()
        profile.home_address_latitude = 45.0
        profile.home_address_longitude = 9.0
        mock_async.reset_mock()
        profile.save()

        called_pks = [call.args[1] for call in mock_async.call_args_list]
        assert days[0].pk in called_pks
        assert days[-1].pk in called_pks

    @patch("accounts.models.async_task")
    def test_skips_completed_trips(self, mock_async, user_factory, trip_factory):
        """Signal does not trigger recalculation for completed trips."""
        from accounts.models import Profile
        from trips.models import Trip

        user = user_factory()
        today = date.today()
        trip = trip_factory(
            author=user,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=5),
        )
        Trip.objects.filter(pk=trip.pk).update(status=Trip.Status.COMPLETED)
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        profile = user.profile
        profile.refresh_from_db()
        profile.home_address_latitude = 45.0
        profile.home_address_longitude = 9.0
        mock_async.reset_mock()
        profile.save()

        day_pks = list(trip.days.values_list("pk", flat=True))
        called_pks = [call.args[1] for call in mock_async.call_args_list]
        assert not any(pk in called_pks for pk in day_pks)

    @patch("accounts.models.async_task")
    def test_skips_archived_trips(self, mock_async, user_factory, trip_factory):
        """Signal does not trigger recalculation for archived trips."""
        from accounts.models import Profile
        from trips.models import Trip

        user = user_factory()
        today = date.today()
        trip = trip_factory(
            author=user,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=5),
        )
        Trip.objects.filter(pk=trip.pk).update(status=Trip.Status.ARCHIVED)
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        profile = user.profile
        profile.refresh_from_db()
        profile.home_address_latitude = 45.0
        profile.home_address_longitude = 9.0
        mock_async.reset_mock()
        profile.save()

        day_pks = list(trip.days.values_list("pk", flat=True))
        called_pks = [call.args[1] for call in mock_async.call_args_list]
        assert not any(pk in called_pks for pk in day_pks)

    @patch("accounts.models.async_task")
    def test_no_recalculation_if_coords_unchanged(
        self, mock_async, user_factory, trip_factory
    ):
        """Signal does not trigger if home coords did not change."""
        from accounts.models import Profile

        user = user_factory()
        today = date.today()
        trip_factory(
            author=user,
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=10),
        )
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        profile = user.profile
        profile.refresh_from_db()
        profile.show_transfer_info = not profile.show_transfer_info
        mock_async.reset_mock()
        profile.save()

        assert mock_async.call_count == 0

    @patch("accounts.models.async_task")
    def test_skips_trip_with_no_days(self, mock_async, user_factory, trip_factory):
        """Signal skips trips that have no days (edge case)."""
        from accounts.models import Profile

        user = user_factory()
        today = date.today()
        trip = trip_factory(
            author=user,
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=5),
        )
        trip.days.all().delete()
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        profile = user.profile
        profile.refresh_from_db()
        profile.home_address_latitude = 45.0
        mock_async.reset_mock()
        profile.save()

        assert mock_async.call_count == 0

    @patch("accounts.models.async_task")
    def test_single_day_trip_triggers_only_one_task(
        self, mock_async, user_factory, trip_factory
    ):
        """Single-day trip: first_day == last_day, so only one async_task call."""
        from accounts.models import Profile

        user = user_factory()
        today = date.today()
        trip = trip_factory(
            author=user,
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=5),
        )
        assert trip.days.count() == 1
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        profile = user.profile
        profile.refresh_from_db()
        profile.home_address_latitude = 45.0
        mock_async.reset_mock()
        profile.save()

        assert mock_async.call_count == 1
