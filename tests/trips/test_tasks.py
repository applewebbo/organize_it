"""Tests for background tasks (issue #237)."""

from datetime import date, timedelta

import pytest

from trips.tasks import fetch_weather_for_active_trips

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
