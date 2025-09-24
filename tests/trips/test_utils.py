from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from tests.test import TestCase
from tests.trips.factories import EventFactory, MealFactory, StayFactory, TripFactory
from trips.utils import (
    annotate_event_overlaps,
    create_day_map,
    generate_cache_key,
    geocode_location,
    get_trips,
    select_best_result,
)

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
        self.assertEqual(len(context["other_trips"]), 2)
        self.assertIn(trip1, context["other_trips"])
        self.assertIn(trip2, context["other_trips"])

    def test_get_trips_with_fav(self):
        """Test get_trips when user has a favorite trip."""
        profile = self.user.profile
        fav_trip = TripFactory(author=self.user)
        other_trip = TripFactory(author=self.user)
        profile.fav_trip = fav_trip
        profile.save()

        context = get_trips(self.user)
        self.assertEqual(context["fav_trip"], fav_trip)
        self.assertEqual(len(context["other_trips"]), 1)
        self.assertIn(other_trip, context["other_trips"])
        self.assertNotIn(fav_trip, context["other_trips"])


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
