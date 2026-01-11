import time as time_module
from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest
import time_machine
from django.contrib.auth import get_user_model
from django.core.cache import cache

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.utils import (
    annotate_event_overlaps,
    convert_google_opening_hours,
    create_day_map,
    download_unsplash_photo,
    generate_cache_key,
    geocode_location,
    get_trips,
    process_trip_image,
    rate_limit_check,
    search_unsplash_photos,
    select_best_result,
)


class TestRateLimitCheck(TestCase):
    @patch("trips.utils.time.sleep")
    @patch("trips.utils.cache.get")
    @patch("trips.utils.cache.set")
    def test_rate_limit_check_no_wait(self, mock_cache_set, mock_cache_get, mock_sleep):
        mock_cache_get.return_value = (
            time_module.time() - 2
        )  # Last request was 2 seconds ago
        rate_limit_check()
        mock_sleep.assert_not_called()
        mock_cache_set.assert_called_once()

    @patch("trips.utils.time.sleep")
    @patch("trips.utils.cache.get")
    @patch("trips.utils.cache.set")
    def test_rate_limit_check_with_wait(
        self, mock_cache_set, mock_cache_get, mock_sleep
    ):
        mock_cache_get.return_value = (
            time_module.time() - 0.5
        )  # Last request was 0.5 seconds ago
        rate_limit_check()
        mock_sleep.assert_called_once_with(pytest.approx(0.5, abs=0.01))
        mock_cache_set.assert_called_once()

    @patch("trips.utils.time.sleep")
    @patch("trips.utils.cache.get")
    @patch("trips.utils.cache.set")
    def test_rate_limit_check_first_request(
        self, mock_cache_set, mock_cache_get, mock_sleep
    ):
        mock_cache_get.return_value = 0  # No previous request
        rate_limit_check()
        mock_sleep.assert_not_called()
        mock_cache_set.assert_called_once()


pytestmark = pytest.mark.django_db
User = get_user_model()


class TestEventOverlaps(TestCase):
    """Test cases for event overlap detection"""

    def test_no_overlaps(self):
        """Test events with no time overlaps"""
        trip = TripFactory()
        day = trip.days.first()

        [
            EventFactory(day=day, start_time=time(9, 0), end_time=time(10, 0)),
            EventFactory(day=day, start_time=time(10, 30), end_time=time(11, 30)),
            EventFactory(day=day, start_time=time(12, 0), end_time=time(13, 0)),
        ]

        annotated_events = annotate_event_overlaps(day.events.all())

        for event in annotated_events:
            assert not event.has_overlap

    def test_overlapping_events(self):
        """Test events with overlapping times"""
        trip = TripFactory()
        day = trip.days.first()

        [
            EventFactory(day=day, start_time=time(9, 0), end_time=time(11, 0)),
            EventFactory(day=day, start_time=time(10, 0), end_time=time(12, 0)),
            EventFactory(
                day=day, start_time=time(12, 30), end_time=time(13, 30)
            ),  # Changed time to avoid overlap
        ]

        annotated_events = annotate_event_overlaps(day.events.all())

        # First two events should overlap
        assert all(e.has_overlap for e in annotated_events[:2])
        # Last event should not overlap
        assert not annotated_events[2].has_overlap

    def test_adjacent_events_no_overlap(self):
        """Test events that are adjacent but don't overlap"""
        trip = TripFactory()
        day = trip.days.first()

        [
            EventFactory(day=day, start_time=time(9, 0), end_time=time(10, 0)),
            EventFactory(day=day, start_time=time(10, 0), end_time=time(11, 0)),
        ]

        annotated_events = annotate_event_overlaps(day.events.all())

        for event in annotated_events:
            assert not event.has_overlap

    def test_events_different_days_no_overlap(self):
        """Test events on different days don't affect each other"""
        trip = TripFactory(start_date=date(2024, 1, 1), end_date=date(2024, 1, 2))
        day1, day2 = trip.days.all()[:2]

        # Create overlapping times but on different days
        [
            EventFactory(day=day1, start_time=time(9, 0), end_time=time(11, 0)),
            EventFactory(day=day2, start_time=time(10, 0), end_time=time(12, 0)),
        ]

        # Get all events and annotate
        annotated_events = annotate_event_overlaps(day1.events.all())

        for event in annotated_events:
            assert not event.has_overlap

    def test_single_event_no_overlap(self):
        """Test single event has no overlap"""
        trip = TripFactory()
        day = trip.days.first()

        EventFactory(day=day, start_time=time(9, 0), end_time=time(11, 0))

        annotated_events = annotate_event_overlaps(day.events.all())

        assert len(annotated_events) == 1
        assert not annotated_events[0].has_overlap


class TestGeocoding(TestCase):
    def setUp(self):
        cache.clear()

    @patch("trips.utils.requests.get")
    def test_geocode_location_success(self, mock_get):
        """Test geocode_location with a successful API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "Colosseum",
                "lat": "41.8902",
                "lon": "12.4922",
                "importance": 0.9,
                "place_rank": 10,
                "address": {"road": "Piazza del Colosseo", "city": "Rome"},
            }
        ]
        mock_get.return_value = mock_response

        results = geocode_location("Colosseum", "Rome")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Colosseum")
        self.assertEqual(results[0]["address"], "Piazza del Colosseo, Rome")
        mock_get.assert_called_once()

    @patch("trips.utils.requests.get")
    def test_geocode_location_no_results(self, mock_get):
        """Test geocode_location when API returns no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        results = geocode_location("Unknown Place", "Nowhere")
        self.assertEqual(results, [])

    @patch("trips.utils.requests.get")
    def test_geocode_location_api_error(self, mock_get):
        """Test geocode_location with an API error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        results = geocode_location("Test", "City")
        self.assertEqual(results, [])

    @patch("trips.utils.requests.get")
    def test_geocode_location_request_exception(self, mock_get):
        """Test geocode_location with a request exception."""
        mock_get.side_effect = Exception("Connection error")

        results = geocode_location("Test", "City")
        self.assertEqual(results, [])

    def test_geocode_location_empty_input(self):
        """Test geocode_location with empty name or city."""
        self.assertIsNone(geocode_location("", "City"))
        self.assertIsNone(geocode_location("Name", ""))
        self.assertIsNone(geocode_location("", ""))

    @patch("trips.utils.requests.get")
    def test_geocode_location_caching(self, mock_get):
        """Test that geocode_location results are cached."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "Test Place"}]
        mock_get.return_value = mock_response

        # First call, should hit the API
        geocode_location("Test Place", "Test City")
        mock_get.assert_called_once()

        # Second call, should use cache
        geocode_location("Test Place", "Test City")
        mock_get.assert_called_once()  # Should not be called again

    def test_select_best_result(self):
        """Test the logic for selecting the best geocoding result."""
        results = [
            {
                "display_name": "Generic Town, Country",
                "importance": 0.5,
                "place_rank": 20,
                "class": "place",
                "type": "town",
                "address": {"town": "Test City"},
            },
            {
                "display_name": "Specific Place, Test City, Country",
                "importance": 0.8,
                "place_rank": 10,
                "address": {"city": "Test City"},
            },
        ]
        best_result = select_best_result(results, "Specific Place", "Test City")
        self.assertEqual(
            best_result["display_name"], "Specific Place, Test City, Country"
        )

    def test_select_best_result_no_results(self):
        """Test select_best_result with no results."""
        self.assertIsNone(select_best_result([], "Name", "City"))

    def test_select_best_result_no_scored_results(self):
        """Test select_best_result with no scored results."""
        results = [
            {"display_name": "A", "address": {}, "importance": 0, "place_rank": 99}
        ]
        best_result = select_best_result(results, "B", "C")
        self.assertEqual(best_result, results[0])


class TestGetTrips(TestCase):
    def setUp(self):
        self.user = self.make_user("user")

    def test_get_trips_no_fav(self):
        """Test get_trips when user has no favorite trip."""
        trip1 = TripFactory(author=self.user)
        trip2 = TripFactory(author=self.user)
        context = get_trips(self.user)
        self.assertIsNone(context["fav_trip"])
        self.assertIsNotNone(context["latest_trip"])
        self.assertIn(trip1, [context["latest_trip"]] + list(context["other_trips"]))
        self.assertIn(trip2, [context["latest_trip"]] + list(context["other_trips"]))

    def test_get_trips_with_fav(self):
        """Test get_trips when user has a favorite trip."""
        profile = self.user.profile
        fav_trip = TripFactory(author=self.user)
        other_trip = TripFactory(author=self.user)
        profile.fav_trip = fav_trip
        profile.save()

        context = get_trips(self.user)
        self.assertEqual(context["fav_trip"], fav_trip)
        self.assertIsNone(context["latest_trip"])
        self.assertEqual(len(context["other_trips"]), 1)
        self.assertIn(other_trip, context["other_trips"])
        self.assertNotIn(fav_trip, context["other_trips"])

    def test_get_trips_fav_with_prefetch(self):
        """Test favorite trip has proper prefetch for days and events."""
        profile = self.user.profile
        fav_trip = TripFactory(
            author=self.user, start_date=date(2024, 1, 1), end_date=date(2024, 1, 3)
        )
        profile.fav_trip = fav_trip
        profile.save()

        day = fav_trip.days.first()
        event = EventFactory(day=day, start_time=time(9, 0), end_time=time(10, 0))

        context = get_trips(self.user)
        self.assertEqual(context["fav_trip"], fav_trip)
        self.assertEqual(len(context["fav_trip"].days.all()), 3)
        self.assertIn(event, context["fav_trip"].days.first().events.all())

    def test_get_trips_fav_with_unpaired_events(self):
        """Test unpaired events are included for favorite trip."""
        from trips.models import Experience

        profile = self.user.profile
        fav_trip = TripFactory(author=self.user)
        profile.fav_trip = fav_trip
        profile.save()

        unpaired_event = Experience.objects.create(
            trip=fav_trip,
            day=None,
            name="Test Event",
            start_time=time(10, 0),
            end_time=time(11, 0),
            address="Test Address",
            city=fav_trip.destination,
        )

        context = get_trips(self.user)
        self.assertIn(unpaired_event.event_ptr, context["unpaired_events"])

    @time_machine.travel("2026-01-15")
    def test_get_trips_latest_in_progress(self):
        """Test latest trip is IN_PROGRESS trip when available."""
        # With time frozen at 2026-01-15, create trips with specific statuses
        TripFactory(
            author=self.user,
            status=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 10),
        )  # NOT_STARTED (in future)
        in_progress_trip = TripFactory(
            author=self.user,
            status=3,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 20),
        )  # IN_PROGRESS (includes today)
        TripFactory(
            author=self.user,
            status=2,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10),
        )  # IMPENDING (soon)

        context = get_trips(self.user)
        self.assertEqual(context["latest_trip"], in_progress_trip)

    @time_machine.travel("2025-12-28")
    def test_get_trips_latest_impending(self):
        """Test latest trip is IMPENDING with earliest start_date."""
        earliest_impending = TripFactory(
            author=self.user,
            status=2,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )
        TripFactory(
            author=self.user,
            status=2,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10),
        )
        TripFactory(
            author=self.user,
            status=2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 10),
        )

        context = get_trips(self.user)
        self.assertEqual(context["latest_trip"].pk, earliest_impending.pk)

    @time_machine.travel("2025-12-01")
    def test_get_trips_latest_by_status(self):
        """Test latest trip ordering by status when no IN_PROGRESS or IMPENDING."""
        not_started = TripFactory(
            author=self.user,
            status=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )
        TripFactory(
            author=self.user,
            status=4,
            start_date=date(2023, 12, 1),
            end_date=date(2023, 12, 10),
        )  # COMPLETED

        context = get_trips(self.user)
        self.assertEqual(context["latest_trip"].pk, not_started.pk)

    def test_get_trips_excludes_archived(self):
        """Test archived trips are excluded from latest and others."""
        TripFactory(author=self.user, status=5)  # ARCHIVED

        context = get_trips(self.user)
        self.assertIsNone(context["latest_trip"])
        self.assertEqual(len(context["other_trips"]), 0)

    def test_get_trips_no_trips(self):
        """Test get_trips when user has no trips."""
        context = get_trips(self.user)
        self.assertIsNone(context["fav_trip"])
        self.assertIsNone(context["latest_trip"])
        self.assertIsNone(context["unpaired_events"])
        self.assertEqual(len(context["other_trips"]), 0)

    def test_get_trips_latest_with_unpaired_events(self):
        """Test unpaired events are included for latest trip."""
        from trips.models import Experience

        trip = TripFactory(author=self.user)
        unpaired_event = Experience.objects.create(
            trip=trip,
            day=None,
            name="Test Event",
            start_time=time(10, 0),
            end_time=time(11, 0),
            address="Test Address",
            city=trip.destination,
        )

        context = get_trips(self.user)
        self.assertEqual(context["latest_trip"], trip)
        self.assertIn(unpaired_event.event_ptr, context["unpaired_events"])

    @time_machine.travel("2026-01-05")
    def test_get_trips_other_trips_exclude_latest(self):
        """Test other_trips excludes the latest trip."""
        trip1 = TripFactory(
            author=self.user,
            status=3,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )  # IN_PROGRESS (will be latest)
        trip2 = TripFactory(
            author=self.user,
            status=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10),
        )
        trip3 = TripFactory(
            author=self.user,
            status=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 10),
        )

        context = get_trips(self.user)
        self.assertEqual(context["latest_trip"], trip1)
        self.assertNotIn(trip1, context["other_trips"])
        self.assertIn(trip2, context["other_trips"])
        self.assertIn(trip3, context["other_trips"])


class TestCacheKey(TestCase):
    def test_generate_cache_key(self):
        """Test cache key generation is consistent and handles whitespace/case."""
        key1 = generate_cache_key("Test Name", "Test City")
        key2 = generate_cache_key(" test name ", " TEST CITY")
        self.assertEqual(key1, key2)
        key3 = generate_cache_key("Another Name", "Test City")
        self.assertNotEqual(key1, key3)


class TestCreateDayMap(TestCase):
    def test_create_day_map_with_next_day_stay(self):
        """Test map creation with a different stay on the next day."""
        trip = TripFactory(start_date=date(2024, 1, 1), end_date=date(2024, 1, 2))
        day1, day2 = trip.days.all()
        stay1 = StayFactory(name="Stay 1", latitude=10, longitude=10)
        stay2 = StayFactory(name="Stay 2", latitude=20, longitude=20)
        day1.stay = stay1
        day1.save()
        day2.stay = stay2
        day2.save()
        meal = MealFactory(name="Dinner", day=day1, latitude=15, longitude=15)

        map_html = create_day_map(day1.events.all(), day1.stay, day2.stay)
        self.assertIn(meal.name, map_html)
        self.assertIn(stay1.name, map_html)
        self.assertIn(
            f"Nextday:{stay2.name.replace(' ', '')}",
            map_html.replace("\\n", "").replace(" ", ""),
        )

    def test_create_day_map_no_locations(self):
        """Test map creation with no locations."""
        trip = TripFactory()
        day = trip.days.first()
        map_html = create_day_map(day.events.all(), None, None)
        self.assertIsNone(map_html)

    @patch("trips.models.geocoder.mapbox")
    def test_create_day_map_with_stay_no_location(self, mock_mapbox):
        """Test map creation with a stay that has no location."""
        mock_g = MagicMock()
        mock_g.latlng = None
        mock_mapbox.return_value = mock_g

        trip = TripFactory()
        day = trip.days.first()
        stay_no_location = StayFactory(
            name="Stay without location", latitude=None, longitude=None
        )
        day.stay = stay_no_location
        day.save()

        stay_no_location.refresh_from_db()

        event = MealFactory(name="Dinner", day=day, latitude=15, longitude=15)

        map_html = create_day_map(day.events.all(), day.stay, None)
        self.assertIn(event.name, map_html)
        self.assertNotIn(stay_no_location.name, map_html)


class TestConvertGoogleOpeningHours(TestCase):
    def test_convert_google_opening_hours_valid_data(self):
        google_hours = {
            "periods": [
                {
                    "open": {"day": 1, "hour": 9, "minute": 0},
                    "close": {"day": 1, "hour": 17, "minute": 0},
                },
                {
                    "open": {"day": 2, "hour": 10, "minute": 30},
                    "close": {"day": 2, "hour": 18, "minute": 30},
                },
            ]
        }
        expected_hours = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "10:30", "close": "18:30"},
        }
        self.assertEqual(convert_google_opening_hours(google_hours), expected_hours)

    def test_convert_google_opening_hours_empty_input(self):
        self.assertIsNone(convert_google_opening_hours(None))
        self.assertIsNone(convert_google_opening_hours({}))
        self.assertIsNone(convert_google_opening_hours({"periods": []}))

    def test_convert_google_opening_hours_missing_keys(self):
        google_hours = {
            "periods": [
                {"open": {"day": 1, "hour": 9}},  # Missing close
                {"close": {"day": 2, "hour": 18}},  # Missing open
            ]
        }
        self.assertIsNone(convert_google_opening_hours(google_hours))

    def test_convert_google_opening_hours_no_minutes(self):
        google_hours = {
            "periods": [
                {"open": {"day": 1, "hour": 9}, "close": {"day": 1, "hour": 17}},
            ]
        }
        expected_hours = {
            "monday": {"open": "09:00", "close": "17:00"},
        }
        self.assertEqual(convert_google_opening_hours(google_hours), expected_hours)

    def test_convert_google_opening_hours_unmapped_day(self):
        google_hours = {
            "periods": [
                {"open": {"day": 99, "hour": 9}, "close": {"day": 99, "hour": 17}},
            ]
        }
        self.assertIsNone(convert_google_opening_hours(google_hours))


class TestUnsplashAPI(TestCase):
    """Test cases for Unsplash API integration"""

    def setUp(self):
        cache.clear()

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "test_key")
    @patch("trips.utils.requests.get")
    def test_search_unsplash_photos_success(self, mock_get):
        """Test successful Unsplash search"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "abc123",
                    "urls": {
                        "regular": "https://example.com/regular.jpg",
                        "small": "https://example.com/small.jpg",
                        "thumb": "https://example.com/thumb.jpg",
                    },
                    "user": {
                        "name": "John Doe",
                        "username": "johndoe",
                        "links": {"html": "https://unsplash.com/@johndoe"},
                    },
                    "links": {
                        "html": "https://unsplash.com/photos/abc123",
                        "download_location": "https://api.unsplash.com/photos/abc123/download",
                    },
                    "alt_description": "Beautiful landscape",
                }
            ]
        }
        mock_get.return_value = mock_response

        photos = search_unsplash_photos("Paris")

        self.assertEqual(len(photos), 1)
        self.assertEqual(photos[0]["id"], "abc123")
        self.assertEqual(photos[0]["user"]["name"], "John Doe")
        mock_get.assert_called_once()

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "test_key")
    @patch("trips.utils.requests.get")
    def test_search_unsplash_photos_cached(self, mock_get):
        """Test that search results are cached"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "cached123",
                    "urls": {
                        "regular": "https://example.com/regular.jpg",
                        "small": "https://example.com/small.jpg",
                        "thumb": "https://example.com/thumb.jpg",
                    },
                    "user": {
                        "name": "Cached User",
                        "username": "cacheduser",
                        "links": {"html": "https://unsplash.com/@cacheduser"},
                    },
                    "links": {
                        "html": "https://unsplash.com/photos/cached123",
                        "download_location": "https://api.unsplash.com/photos/cached123/download",
                    },
                    "alt_description": "Cached image",
                }
            ]
        }
        mock_get.return_value = mock_response

        # First call
        search_unsplash_photos("Paris")
        self.assertEqual(mock_get.call_count, 1)

        # Second call should use cache
        search_unsplash_photos("Paris")
        self.assertEqual(mock_get.call_count, 1)  # Still 1, not called again

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "test_key")
    @patch("trips.utils.requests.get")
    def test_search_unsplash_photos_timeout(self, mock_get):
        """Test Unsplash API timeout handling"""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        photos = search_unsplash_photos("Paris")

        self.assertIsNone(photos)

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "test_key")
    @patch("trips.utils.requests.get")
    def test_search_unsplash_photos_api_error(self, mock_get):
        """Test Unsplash API error handling"""
        import requests

        mock_get.side_effect = requests.RequestException("API Error")

        photos = search_unsplash_photos("Paris")

        self.assertIsNone(photos)

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "")
    def test_search_unsplash_photos_no_api_key(self):
        """Test search without API key configured"""
        photos = search_unsplash_photos("Paris")

        self.assertIsNone(photos)

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "test_key")
    @patch("trips.utils.requests.get")
    def test_download_unsplash_photo_success(self, mock_get):
        """Test successful photo download from Unsplash"""
        # Mock download tracking response
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200

        # Mock image download response
        mock_image_response = MagicMock()
        mock_image_response.status_code = 200
        mock_image_response.content = b"fake_image_data"

        mock_get.side_effect = [mock_download_response, mock_image_response]

        photo_data = {
            "id": "abc123",
            "urls": {"regular": "https://example.com/image.jpg"},
            "user": {
                "name": "John Doe",
                "profile": "https://unsplash.com/@johndoe",
            },
            "links": {
                "html": "https://unsplash.com/photos/abc123",
                "download_location": "https://api.unsplash.com/photos/abc123/download",
            },
        }

        content, metadata = download_unsplash_photo(photo_data)

        self.assertEqual(content, b"fake_image_data")
        self.assertEqual(metadata["source"], "unsplash")
        self.assertEqual(metadata["unsplash_id"], "abc123")
        self.assertEqual(metadata["photographer"], "John Doe")
        self.assertEqual(mock_get.call_count, 2)  # Download tracking + image download

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "test_key")
    @patch("trips.utils.requests.get")
    def test_download_unsplash_photo_error(self, mock_get):
        """Test download error handling"""
        import requests

        mock_get.side_effect = requests.RequestException("Download failed")

        photo_data = {
            "id": "abc123",
            "urls": {"regular": "https://example.com/image.jpg"},
            "links": {"download_location": "https://api.unsplash.com/download"},
        }

        content, metadata = download_unsplash_photo(photo_data)

        self.assertIsNone(content)
        self.assertIsNone(metadata)

    @patch("django.conf.settings.UNSPLASH_ACCESS_KEY", "")
    def test_download_unsplash_photo_no_api_key(self):
        """Test download without API key configured"""
        photo_data = {
            "id": "abc123",
            "urls": {"regular": "https://example.com/image.jpg"},
            "links": {"download_location": "https://api.unsplash.com/download"},
        }

        content, metadata = download_unsplash_photo(photo_data)

        self.assertIsNone(content)
        self.assertIsNone(metadata)


class TestImageProcessing(TestCase):
    """Test cases for image processing utilities"""

    def test_process_trip_image_from_bytes(self):
        """Test processing image from bytes"""
        from io import BytesIO

        from PIL import Image

        # Create a test image
        img = Image.new("RGB", (800, 600), color="red")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_bytes = img_io.getvalue()

        processed = process_trip_image(img_bytes)

        self.assertIsNotNone(processed)
        self.assertEqual(processed.content_type, "image/jpeg")

    def test_process_trip_image_landscape_orientation(self):
        """Test that portrait images are rotated to landscape"""
        from io import BytesIO

        from PIL import Image

        # Create a portrait image (height > width)
        img = Image.new("RGB", (600, 800), color="blue")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_bytes = img_io.getvalue()

        processed = process_trip_image(img_bytes)

        self.assertIsNotNone(processed)
        # Verify image was rotated by checking it can be opened
        processed_img = Image.open(processed)
        self.assertGreater(processed_img.width, processed_img.height)

    def test_process_trip_image_resize_large(self):
        """Test that large images are resized"""
        from io import BytesIO

        from PIL import Image

        # Create an oversized image
        img = Image.new("RGB", (3000, 2000), color="green")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_bytes = img_io.getvalue()

        processed = process_trip_image(img_bytes)

        self.assertIsNotNone(processed)
        processed_img = Image.open(processed)
        self.assertLessEqual(processed_img.width, 1200)
        self.assertLessEqual(processed_img.height, 800)

    def test_process_trip_image_invalid_data(self):
        """Test processing invalid image data"""
        result = process_trip_image(b"not an image")

        self.assertIsNone(result)

    def test_process_trip_image_from_uploaded_file(self):
        """Test processing from UploadedFile object"""
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        # Create test image
        img = Image.new("RGB", (800, 600), color="blue")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_io.seek(0)

        uploaded_file = SimpleUploadedFile(
            "test.jpg", img_io.read(), content_type="image/jpeg"
        )

        processed = process_trip_image(uploaded_file)

        self.assertIsNotNone(processed)

    def test_process_trip_image_large_file(self):
        """Test processing large file (>2MB) triggers size warning"""
        from io import BytesIO
        from unittest.mock import patch

        import numpy as np
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        # Create large image with random pixels to prevent compression
        # This ensures the file will be > 2MB
        width, height = 3000, 2500
        # Generate random RGB data
        random_data = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        img = Image.fromarray(random_data, "RGB")

        img_io = BytesIO()
        img.save(img_io, "JPEG", quality=100)
        img_io.seek(0)
        img_bytes = img_io.read()

        # Verify the image is actually > 2MB
        size_mb = len(img_bytes) / (1024 * 1024)
        self.assertGreater(size_mb, 2, f"Test image size {size_mb:.2f}MB is not > 2MB")

        uploaded_file = SimpleUploadedFile(
            "large.jpg", img_bytes, content_type="image/jpeg"
        )

        # Mock logger to verify warning is called
        with patch("trips.utils.logger.warning") as mock_warning:
            # Should still process and resize
            processed = process_trip_image(uploaded_file)

            self.assertIsNotNone(processed)
            # Verify warning was logged
            mock_warning.assert_called_once()
            # Check warning message contains size info
            warning_msg = mock_warning.call_args[0][0]
            self.assertIn("Image too large", warning_msg)
            self.assertIn("MB", warning_msg)

        processed_img = Image.open(processed)
        # Should be resized
        self.assertLessEqual(processed_img.width, 1200)
        self.assertLessEqual(processed_img.height, 800)

    def test_process_trip_image_rgba_conversion(self):
        """Test RGBA to RGB conversion"""
        from io import BytesIO

        from PIL import Image

        # Create RGBA image
        img = Image.new("RGBA", (800, 600), color=(255, 0, 0, 128))
        img_io = BytesIO()
        img.save(img_io, "PNG")
        img_bytes = img_io.getvalue()

        processed = process_trip_image(img_bytes)

        self.assertIsNotNone(processed)
        processed_img = Image.open(processed)
        self.assertEqual(processed_img.mode, "RGB")

    def test_process_trip_image_wide_aspect_ratio(self):
        """Test image with wide aspect ratio (wider than target)"""
        from io import BytesIO

        from PIL import Image

        # Create very wide image (2400x600 = 4:1 ratio)
        img = Image.new("RGB", (2400, 600), color="yellow")
        img_io = BytesIO()
        img.save(img_io, "JPEG")
        img_bytes = img_io.getvalue()

        processed = process_trip_image(img_bytes)

        self.assertIsNotNone(processed)
        processed_img = Image.open(processed)
        # Should be resized to max width 1200
        self.assertLessEqual(processed_img.width, 1200)
        self.assertLessEqual(processed_img.height, 800)


class TestCSVFunctions(TestCase):
    """Test CSV loading and search functions for airports and stations"""

    def test_load_airports(self):
        """Test loading airports from CSV"""
        from trips.utils import load_airports

        airports = load_airports()

        self.assertIsInstance(airports, list)
        self.assertGreater(len(airports), 0)

        # Check first airport structure
        first_airport = airports[0]
        self.assertIn("iata_code", first_airport)
        self.assertIn("name", first_airport)
        self.assertIn("city", first_airport)
        self.assertIn("latitude", first_airport)
        self.assertIn("longitude", first_airport)

        # Test cache works (second call should use cache)
        airports2 = load_airports()
        self.assertIs(airports, airports2)  # Should be same object

    def test_load_train_stations(self):
        """Test loading train stations from CSV"""
        from trips.utils import load_train_stations

        stations = load_train_stations()

        self.assertIsInstance(stations, list)
        self.assertGreater(len(stations), 0)

        # Check first station structure
        first_station = stations[0]
        self.assertIn("id", first_station)
        self.assertIn("name", first_station)
        self.assertIn("country", first_station)
        self.assertIn("latitude", first_station)
        self.assertIn("longitude", first_station)

        # Test cache works
        stations2 = load_train_stations()
        self.assertIs(stations, stations2)

    def test_search_airports_by_code(self):
        """Test searching airports by IATA code"""
        from trips.utils import search_airports

        results = search_airports("FCO", limit=5)

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        # Should find Rome Fiumicino
        self.assertTrue(any("FCO" in r["iata_code"] for r in results))

    def test_search_airports_by_city(self):
        """Test searching airports by city name"""
        from trips.utils import search_airports

        results = search_airports("Rome", limit=5)

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_search_airports_limit(self):
        """Test search airports respects limit"""
        from trips.utils import search_airports

        results = search_airports("a", limit=3)

        self.assertLessEqual(len(results), 3)

    def test_search_train_stations_by_name(self):
        """Test searching train stations by name"""
        from trips.utils import search_train_stations

        results = search_train_stations("Barcelona", limit=5)

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_search_train_stations_by_country(self):
        """Test searching train stations by country code"""
        from trips.utils import search_train_stations

        results = search_train_stations("ES", limit=5)

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_search_train_stations_limit(self):
        """Test search train stations respects limit"""
        from trips.utils import search_train_stations

        results = search_train_stations("a", limit=2)

        self.assertLessEqual(len(results), 2)

    def test_search_train_stations_no_results(self):
        """Test search train stations returns empty list when no match"""
        from trips.utils import search_train_stations

        results = search_train_stations("NONEXISTENT_STATION_12345", limit=10)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_get_airport_by_iata_found(self):
        """Test getting specific airport by IATA code"""
        from trips.utils import get_airport_by_iata

        airport = get_airport_by_iata("FCO")

        self.assertIsNotNone(airport)
        self.assertEqual(airport["iata_code"], "FCO")
        self.assertIn("Rome", airport["name"] + airport["city"])

    def test_get_airport_by_iata_not_found(self):
        """Test getting non-existent airport returns None"""
        from trips.utils import get_airport_by_iata

        airport = get_airport_by_iata("XXX")

        self.assertIsNone(airport)

    def test_get_station_by_id_found(self):
        """Test getting specific station by ID"""
        from trips.utils import get_station_by_id, load_train_stations

        # Get first station ID from CSV
        stations = load_train_stations()
        first_id = stations[0]["id"]

        station = get_station_by_id(first_id)

        self.assertIsNotNone(station)
        self.assertEqual(station["id"], first_id)

    def test_get_station_by_id_not_found(self):
        """Test getting non-existent station returns None"""
        from trips.utils import get_station_by_id

        station = get_station_by_id("999999")

        self.assertIsNone(station)


class TestMapWithMainTransfers(TestCase):
    """Test create_day_map integration with main transfers"""

    def test_create_day_map_with_arrival_transfer(self):
        """Test map includes arrival transfer on first day"""
        from trips.models import Event, MainTransfer
        from trips.utils import create_day_map

        trip = TripFactory()
        day1 = trip.days.first()

        # Create a stay so the map gets generated
        stay = StayFactory(day=day1)

        # Create arrival transfer with coordinates
        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Rome Airport",
            origin_code="FCO",
            origin_latitude=41.8002,
            origin_longitude=12.2389,
            destination_name="Barcelona Airport",
            destination_code="BCN",
            destination_latitude=41.2971,
            destination_longitude=2.0833,
            start_time="10:00",
            end_time="12:00",
        )

        # Create day map
        day_map = create_day_map(
            Event.objects.none(), stay=stay, next_day_stay=None, day=day1
        )

        self.assertIsNotNone(day_map)
        # Map should include the arrival transfer destination

    def test_create_day_map_with_departure_transfer(self):
        """Test map includes departure transfer on last day"""
        from trips.models import Event, MainTransfer
        from trips.utils import create_day_map

        trip = TripFactory(
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)
        )  # 3 days trip
        last_day = trip.days.last()

        # Verify last day number matches total days
        total_days = trip.days.count()
        self.assertEqual(last_day.number, total_days)

        # Create a stay so the map gets generated
        stay = StayFactory(day=last_day, latitude=41.3792, longitude=2.1404)

        # Create departure transfer with coordinates
        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.TRAIN,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="Barcelona Station",
            origin_code="BCN",
            origin_latitude=41.3792,
            origin_longitude=2.1404,
            destination_name="Madrid Station",
            destination_code="MAD",
            destination_latitude=40.4168,
            destination_longitude=-3.7038,
            start_time="15:00",
            end_time="18:00",
        )

        # Create day map for last day
        day_map = create_day_map(
            Event.objects.none(), stay=stay, next_day_stay=None, day=last_day
        )

        self.assertIsNotNone(day_map)
        self.assertIn("Barcelona Station", day_map)
        # Map should include the departure transfer origin marker

    def test_create_day_map_with_departure_transfer_no_coordinates(self):
        """Test map without departure transfer coordinates"""
        from trips.models import Event, MainTransfer
        from trips.utils import create_day_map

        trip = TripFactory(
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)
        )  # 3 days trip
        last_day = trip.days.last()

        # Create a stay so the map gets generated
        stay = StayFactory(day=last_day, latitude=41.3792, longitude=2.1404)

        # Create departure transfer WITHOUT coordinates
        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.TRAIN,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="Barcelona Station",
            origin_code="BCN",
            origin_latitude=None,
            origin_longitude=None,
            destination_name="Madrid Station",
            destination_code="MAD",
            destination_latitude=40.4168,
            destination_longitude=-3.7038,
            start_time="15:00",
            end_time="18:00",
        )

        # Create day map for last day
        day_map = create_day_map(
            Event.objects.none(), stay=stay, next_day_stay=None, day=last_day
        )

        self.assertIsNotNone(day_map)
        # Map should be created but without departure marker

    def test_create_day_map_with_both_transfers(self):
        """Test map with both arrival and departure transfers"""
        from trips.models import Event, MainTransfer
        from trips.utils import create_day_map

        trip = TripFactory()
        day1 = trip.days.first()
        last_day = trip.days.last()

        # Create stays so maps get generated
        stay1 = StayFactory(day=day1)
        stay_last = StayFactory(day=last_day)

        # Create both transfers
        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Rome",
            destination_name="Barcelona",
            destination_latitude=41.2971,
            destination_longitude=2.0833,
            start_time="10:00",
            end_time="12:00",
        )

        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="Barcelona",
            origin_latitude=41.2971,
            origin_longitude=2.0833,
            destination_name="Rome",
            start_time="18:00",
            end_time="20:00",
        )

        # Test first day map
        day1_map = create_day_map(
            Event.objects.none(), stay=stay1, next_day_stay=None, day=day1
        )
        self.assertIsNotNone(day1_map)

        # Test last day map
        last_day_map = create_day_map(
            Event.objects.none(), stay=stay_last, next_day_stay=None, day=last_day
        )
        self.assertIsNotNone(last_day_map)

    def test_create_day_map_with_car_transfer(self):
        """Test map includes car transfer with correct icon"""
        from trips.models import Event, MainTransfer
        from trips.utils import create_day_map

        trip = TripFactory()
        day1 = trip.days.first()
        stay = StayFactory(day=day1)

        # Create arrival transfer with CAR type
        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Home",
            destination_name="Hotel",
            destination_latitude=41.2971,
            destination_longitude=2.0833,
            start_time="10:00",
            end_time="12:00",
        )

        day_map = create_day_map(
            Event.objects.none(), stay=stay, next_day_stay=None, day=day1
        )
        self.assertIsNotNone(day_map)
        self.assertIn("car", day_map)

    def test_create_day_map_with_other_transfer(self):
        """Test map includes other transfer type with correct icon"""
        from trips.models import Event, MainTransfer
        from trips.utils import create_day_map

        trip = TripFactory()
        day1 = trip.days.first()
        stay = StayFactory(day=day1)

        # Create arrival transfer with OTHER type
        MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Port",
            destination_name="Hotel",
            destination_latitude=41.2971,
            destination_longitude=2.0833,
            start_time="10:00",
            end_time="12:00",
        )

        day_map = create_day_map(
            Event.objects.none(), stay=stay, next_day_stay=None, day=day1
        )
        self.assertIsNotNone(day_map)
        self.assertIn("person-walking", day_map)
