"""Tests for background tasks (issue #237)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from tests.trips.factories import ExperienceFactory, StayFactory
from trips.tasks import (
    _get_day_coords,
    calculate_day_transfer,
    download_trip_unsplash_photo,
    fetch_weather_for_active_trips,
)

pytestmark = pytest.mark.django_db

TODAY = date.today()

MOCK_PHOTO_DATA = {
    "id": "photo123",
    "urls": {"regular": "https://example.com/photo.jpg"},
    "user": {"name": "Test Photographer", "profile": "https://unsplash.com/@test"},
    "links": {
        "html": "https://unsplash.com/photos/photo123",
        "download_location": "https://api.unsplash.com/download",
    },
}


class TestDownloadTripUnsplashPhoto:
    def test_attaches_photo_to_trip(self, user_factory, trip_factory):
        from io import BytesIO

        from django.core.files.uploadedfile import InMemoryUploadedFile

        user = user_factory()
        trip = trip_factory(author=user)
        fake_file = InMemoryUploadedFile(
            BytesIO(b"processed"), "ImageField", "test.jpg", "image/jpeg", 1024, None
        )

        with patch("trips.utils.download_unsplash_photo") as mock_dl:
            with patch("trips.utils.process_trip_image", return_value=fake_file):
                mock_dl.return_value = (b"img_bytes", {"source": "unsplash"})
                download_trip_unsplash_photo(trip.pk, MOCK_PHOTO_DATA)

        trip.refresh_from_db()
        assert trip.image_metadata == {"source": "unsplash"}

    def test_skips_if_trip_not_found(self):
        download_trip_unsplash_photo(99999, MOCK_PHOTO_DATA)  # no error

    def test_skips_if_download_fails(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)

        with patch("trips.utils.download_unsplash_photo", return_value=(None, None)):
            download_trip_unsplash_photo(trip.pk, MOCK_PHOTO_DATA)

        trip.refresh_from_db()
        assert not trip.image

    def test_skips_if_processing_fails(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)

        with patch("trips.utils.download_unsplash_photo", return_value=(b"data", {})):
            with patch("trips.utils.process_trip_image", return_value=None):
                download_trip_unsplash_photo(trip.pk, MOCK_PHOTO_DATA)


class TestFetchWeatherForActiveTrips:
    def test_processes_impending_trips(self, user_factory, trip_factory):
        user = user_factory()
        # Start date within 7 days → IMPENDING
        trip_factory(
            author=user,
            start_date=TODAY + timedelta(days=2),
            end_date=TODAY + timedelta(days=5),
        )
        result = fetch_weather_for_active_trips()
        assert "1 trip(s)" in result

    def test_processes_in_progress_trips(self, user_factory, trip_factory):
        user = user_factory()
        # Start date today or past, end date future → IN_PROGRESS
        trip_factory(author=user, start_date=TODAY, end_date=TODAY + timedelta(days=5))
        result = fetch_weather_for_active_trips()
        assert "1 trip(s)" in result

    def test_skips_not_started_trips(self, user_factory, trip_factory):
        user = user_factory()
        # Start date more than 7 days away → NOT_STARTED
        trip_factory(
            author=user,
            start_date=TODAY + timedelta(days=30),
            end_date=TODAY + timedelta(days=35),
        )
        result = fetch_weather_for_active_trips()
        assert "0 trip(s)" in result

    def test_skips_completed_trips(self, user_factory, trip_factory):
        user = user_factory()
        # End date in the past → COMPLETED
        trip_factory(
            author=user,
            start_date=TODAY - timedelta(days=10),
            end_date=TODAY - timedelta(days=1),
        )
        result = fetch_weather_for_active_trips()
        assert "0 trip(s)" in result

    def test_processes_multiple_active_trips(self, user_factory, trip_factory):
        user = user_factory()
        trip_factory(
            author=user,
            start_date=TODAY + timedelta(days=2),
            end_date=TODAY + timedelta(days=5),
        )
        trip_factory(author=user, start_date=TODAY, end_date=TODAY + timedelta(days=3))
        trip_factory(
            author=user,
            start_date=TODAY + timedelta(days=30),
            end_date=TODAY + timedelta(days=35),
        )
        result = fetch_weather_for_active_trips()
        assert "2 trip(s)" in result

    def test_returns_summary_string(self):
        result = fetch_weather_for_active_trips()
        assert isinstance(result, str)
        assert "trip(s)" in result


class TestGetDayCoords:
    def test_returns_stay_coords_if_present(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        stay = StayFactory(latitude=45.0, longitude=9.0)
        stay.days.set([day])
        day.refresh_from_db()
        lat, lng = _get_day_coords(day)
        assert lat == 45.0
        assert lng == 9.0

    def test_returns_event_coords_if_no_stay(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, latitude=44.0, longitude=8.0)
        day.refresh_from_db()
        lat, lng = _get_day_coords(day)
        assert lat == 44.0
        assert lng == 8.0

    def test_returns_none_if_no_stay_or_event(self, user_factory, trip_factory):
        from trips.models import Trip

        user = user_factory()
        trip = trip_factory(author=user)
        Trip.objects.filter(pk=trip.pk).update(
            destination_latitude=None, destination_longitude=None
        )
        day = trip.days.first()
        day.refresh_from_db()
        lat, lng = _get_day_coords(day)
        assert lat is None
        assert lng is None

    def test_returns_trip_destination_coords_as_fallback(
        self, user_factory, trip_factory
    ):
        from trips.models import Trip

        user = user_factory()
        trip = trip_factory(author=user)
        Trip.objects.filter(pk=trip.pk).update(
            destination_latitude=41.9, destination_longitude=12.5
        )
        day = trip.days.first()
        day.refresh_from_db()
        lat, lng = _get_day_coords(day)
        assert lat == 41.9
        assert lng == 12.5

    def test_stay_without_coords_falls_back_to_event(self, user_factory, trip_factory):
        from trips.models import Stay

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        stay = StayFactory()
        Stay.objects.filter(pk=stay.pk).update(latitude=None, longitude=None)
        stay.days.set([day])
        ExperienceFactory(trip=trip, day=day, latitude=43.0, longitude=10.0)
        day.refresh_from_db()
        lat, lng = _get_day_coords(day)
        assert lat == 43.0
        assert lng == 10.0

    def test_destination_coords_take_priority(self, user_factory, trip_factory):
        from trips.models import Day

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        Day.objects.filter(pk=day.pk).update(
            destination_latitude=42.0, destination_longitude=11.0
        )
        stay = StayFactory(latitude=45.0, longitude=9.0)
        stay.days.set([day])
        day.refresh_from_db()
        lat, lng = _get_day_coords(day)
        assert lat == 42.0
        assert lng == 11.0


class TestCalculateDayTransfer:
    def test_clears_fields_if_same_destination(self, user_factory, trip_factory):
        """day_pk = first day of arriving stage; prev has same dest → clear."""
        from trips.models import Day

        user = user_factory()
        trip = trip_factory(author=user)
        days = list(trip.days.order_by("number"))
        # days[1] arrives from days[0] with same destination
        Day.objects.filter(pk=days[1].pk).update(
            transfer_duration_from_prev=60, transfer_distance_from_prev=100
        )
        calculate_day_transfer(days[1].pk)
        days[1].refresh_from_db()
        assert days[1].transfer_duration_from_prev is None
        assert days[1].transfer_distance_from_prev is None

    def test_clears_fields_if_no_prev_day(self, user_factory, trip_factory):
        """First day of trip has no prev → clear."""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.order_by("number").first()
        calculate_day_transfer(day.pk)
        day.refresh_from_db()
        assert day.transfer_duration_from_prev is None

    def test_clears_fields_if_no_coords(self, user_factory, trip_factory):
        """prev and day have different dest but no coords → clear on arriving day."""
        user = user_factory()
        trip = trip_factory(author=user)
        days = list(trip.days.order_by("number"))
        days[1].destination = f"NOT_{trip.destination}"
        days[1].save()
        calculate_day_transfer(days[1].pk)
        days[1].refresh_from_db()
        assert days[1].transfer_duration_from_prev is None

    def test_does_nothing_if_day_not_found(self):
        calculate_day_transfer(99999)

    @patch("trips.utils.geocoding.requests.get")
    def test_saves_duration_and_distance_from_api(
        self, mock_get, user_factory, trip_factory
    ):
        """Saves transfer on the arriving day (days[1]) using prev (days[0]) coords."""
        user = user_factory()
        trip = trip_factory(author=user)
        days = list(trip.days.order_by("number"))
        days[1].destination = f"NOT_{trip.destination}"
        days[1].save()
        stay0 = StayFactory(latitude=45.0, longitude=9.0)
        stay0.days.set([days[0]])
        stay1 = StayFactory(latitude=43.0, longitude=11.0)
        stay1.days.set([days[1]])
        mock_get.return_value.json.return_value = {
            "routes": [{"duration": 7200, "distance": 270000}]
        }
        mock_get.return_value.raise_for_status = lambda: None
        calculate_day_transfer(days[1].pk)
        days[1].refresh_from_db()
        assert days[1].transfer_duration_from_prev == 120
        assert days[1].transfer_distance_from_prev == 270

    @patch("trips.utils.geocoding.requests.get")
    def test_handles_api_error_gracefully(self, mock_get, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        days = list(trip.days.order_by("number"))
        days[1].destination = f"NOT_{trip.destination}"
        days[1].save()
        stay0 = StayFactory(latitude=45.0, longitude=9.0)
        stay0.days.set([days[0]])
        stay1 = StayFactory(latitude=43.0, longitude=11.0)
        stay1.days.set([days[1]])
        mock_get.side_effect = Exception("API error")
        calculate_day_transfer(days[1].pk)
        days[1].refresh_from_db()
        assert days[1].transfer_duration_from_prev is None

    @patch("trips.utils.geocoding.requests.get")
    def test_handles_empty_routes(self, mock_get, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        days = list(trip.days.order_by("number"))
        days[1].destination = f"NOT_{trip.destination}"
        days[1].save()
        stay0 = StayFactory(latitude=45.0, longitude=9.0)
        stay0.days.set([days[0]])
        stay1 = StayFactory(latitude=43.0, longitude=11.0)
        stay1.days.set([days[1]])
        mock_get.return_value.json.return_value = {"routes": []}
        mock_get.return_value.raise_for_status = lambda: None
        calculate_day_transfer(days[1].pk)
        days[1].refresh_from_db()
        assert days[1].transfer_duration_from_prev is None

    # --- Home address tests (issue #309) ---

    @patch("trips.utils.geocoding.requests.get")
    def test_uses_home_as_origin_for_day1_without_arrival_transfer(
        self, mock_get, user_factory, trip_factory
    ):
        """Day 1, no ARRIVAL MainTransfer, profile has home coords → calculates from home."""
        from accounts.models import Profile

        user = user_factory()
        trip = trip_factory(author=user)
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        day1 = trip.days.order_by("number").first()
        stay = StayFactory(latitude=43.0, longitude=11.0)
        stay.days.set([day1])
        mock_get.return_value.json.return_value = {
            "routes": [{"duration": 3600, "distance": 180000}]
        }
        mock_get.return_value.raise_for_status = lambda: None
        calculate_day_transfer(day1.pk)
        day1.refresh_from_db()
        assert day1.transfer_duration_from_prev == 60
        assert day1.transfer_distance_from_prev == 180

    def test_clears_fields_if_day1_has_arrival_main_transfer(
        self, user_factory, trip_factory, main_transfer_factory
    ):
        """Day 1 with ARRIVAL MainTransfer → clear from_prev fields."""
        from accounts.models import Profile
        from trips.models import Day, MainTransfer

        user = user_factory()
        trip = trip_factory(author=user)
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        main_transfer_factory(trip=trip, direction=MainTransfer.Direction.ARRIVAL)
        day1 = trip.days.order_by("number").first()
        Day.objects.filter(pk=day1.pk).update(
            transfer_duration_from_prev=60, transfer_distance_from_prev=100
        )
        calculate_day_transfer(day1.pk)
        day1.refresh_from_db()
        assert day1.transfer_duration_from_prev is None
        assert day1.transfer_distance_from_prev is None

    def test_clears_fields_if_day1_no_home_coords(self, user_factory, trip_factory):
        """Day 1, no ARRIVAL, but profile has no home coords → clear."""
        day1 = trip_factory(author=user_factory()).days.order_by("number").first()
        calculate_day_transfer(day1.pk)
        day1.refresh_from_db()
        assert day1.transfer_duration_from_prev is None

    def test_clears_fields_if_day1_home_coords_but_no_day_coords(
        self, user_factory, trip_factory
    ):
        """Day 1, home has coords, day and trip have no geocoords → clear."""
        from accounts.models import Profile
        from trips.models import Trip

        user = user_factory()
        trip = trip_factory(author=user)
        Trip.objects.filter(pk=trip.pk).update(
            destination_latitude=None, destination_longitude=None
        )
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        day1 = trip.days.order_by("number").first()
        calculate_day_transfer(day1.pk)
        day1.refresh_from_db()
        assert day1.transfer_duration_from_prev is None

    @patch("trips.utils.geocoding.requests.get")
    def test_saves_to_home_for_last_day_without_departure_transfer(
        self, mock_get, user_factory, trip_factory
    ):
        """Last day, no DEPARTURE MainTransfer, home has coords → saves to_home fields."""
        from accounts.models import Profile

        user = user_factory()
        trip = trip_factory(author=user)
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        last_day = trip.days.order_by("number").last()
        stay = StayFactory(latitude=43.0, longitude=11.0)
        stay.days.set([last_day])
        mock_get.return_value.json.return_value = {
            "routes": [{"duration": 5400, "distance": 240000}]
        }
        mock_get.return_value.raise_for_status = lambda: None
        calculate_day_transfer(last_day.pk)
        last_day.refresh_from_db()
        assert last_day.transfer_to_home_duration == 90
        assert last_day.transfer_to_home_distance == 240

    def test_clears_to_home_for_last_day_with_departure_transfer(
        self, user_factory, trip_factory, main_transfer_factory
    ):
        """Last day with DEPARTURE MainTransfer → clear to_home fields."""
        from accounts.models import Profile
        from trips.models import Day, MainTransfer

        user = user_factory()
        trip = trip_factory(author=user)
        Profile.objects.filter(user=user).update(
            home_address_latitude=44.0, home_address_longitude=8.0
        )
        main_transfer_factory(trip=trip, direction=MainTransfer.Direction.DEPARTURE)
        last_day = trip.days.order_by("number").last()
        Day.objects.filter(pk=last_day.pk).update(
            transfer_to_home_duration=90, transfer_to_home_distance=240
        )
        calculate_day_transfer(last_day.pk)
        last_day.refresh_from_db()
        assert last_day.transfer_to_home_duration is None
        assert last_day.transfer_to_home_distance is None

    def test_clears_to_home_if_not_last_day(self, user_factory, trip_factory):
        """Non-last day → to_home fields are cleared."""
        from trips.models import Day

        user = user_factory()
        trip = trip_factory(author=user)
        days = list(trip.days.order_by("number"))
        Day.objects.filter(pk=days[0].pk).update(
            transfer_to_home_duration=90, transfer_to_home_distance=240
        )
        calculate_day_transfer(days[0].pk)
        days[0].refresh_from_db()
        assert days[0].transfer_to_home_duration is None
        assert days[0].transfer_to_home_distance is None

    def test_clears_to_home_if_last_day_no_home_coords(
        self, user_factory, trip_factory
    ):
        """Last day, no home coords → to_home fields are cleared."""
        from trips.models import Day

        user = user_factory()
        trip = trip_factory(author=user)
        last_day = trip.days.order_by("number").last()
        Day.objects.filter(pk=last_day.pk).update(
            transfer_to_home_duration=90, transfer_to_home_distance=240
        )
        calculate_day_transfer(last_day.pk)
        last_day.refresh_from_db()
        assert last_day.transfer_to_home_duration is None
        assert last_day.transfer_to_home_distance is None
