"""Tests for background tasks (issue #237)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from tests.trips.factories import ExperienceFactory, StayFactory
from trips.tasks import (
    _get_day_coords,
    calculate_day_transfer,
    fetch_weather_for_active_trips,
)

pytestmark = pytest.mark.django_db

TODAY = date.today()


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
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        lat, lng = _get_day_coords(day)
        assert lat is None
        assert lng is None

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

    @patch("trips.tasks.requests.get")
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

    @patch("trips.tasks.requests.get")
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

    @patch("trips.tasks.requests.get")
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
