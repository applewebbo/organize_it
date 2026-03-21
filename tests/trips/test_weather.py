"""Tests for weather forecast utilities (issue #237)."""

from datetime import date, timedelta

import pytest

from trips.models import Event, Stay
from trips.weather import (
    WMO_CODE_MAP,
    get_coordinates_for_day,
    get_wmo_info,
    parse_weather_response,
)

pytestmark = pytest.mark.django_db


class TestWmoCodeMap:
    def test_all_standard_codes_present(self):
        expected = {
            0,
            1,
            2,
            3,
            45,
            48,
            51,
            53,
            55,
            56,
            57,
            61,
            63,
            65,
            66,
            67,
            71,
            73,
            75,
            77,
            80,
            81,
            82,
            85,
            86,
            95,
            96,
            99,
        }
        assert expected == set(WMO_CODE_MAP.keys())

    def test_each_entry_has_icon_and_label(self):
        for code, info in WMO_CODE_MAP.items():
            assert "icon" in info, f"Missing icon for WMO code {code}"
            assert "label" in info, f"Missing label for WMO code {code}"
            assert info["icon"].startswith("ph-"), (
                f"Icon for code {code} must be a Phosphor class"
            )

    def test_get_wmo_info_known_code(self):
        info = get_wmo_info(0)
        assert info["icon"] == "ph-sun"
        assert info["label"] == "Clear sky"

    def test_get_wmo_info_unknown_code_returns_fallback(self):
        info = get_wmo_info(999)
        assert info["icon"] == "ph-cloud"
        assert info["label"] == "Unknown"


class TestParseWeatherResponse:
    def test_returns_correct_data_for_today(self, open_meteo_response):
        today = date.today()
        result = parse_weather_response(open_meteo_response, today)
        assert result is not None
        assert result["temperature_max"] == 18.5
        assert result["temperature_min"] == 8.1
        assert result["precipitation_sum"] == 0.0
        assert result["wind_speed_max"] == 12.0
        assert result["weather_code"] == 0
        assert result["weather_icon"] == "ph-sun"
        assert result["weather_label"] == "Clear sky"

    def test_returns_correct_data_for_future_day(self, open_meteo_response):
        target = date.today() + timedelta(days=3)
        result = parse_weather_response(open_meteo_response, target)
        assert result is not None
        assert result["temperature_max"] == 12.3
        assert result["weather_code"] == 61

    def test_returns_none_for_date_not_in_response(self, open_meteo_response):
        far_future = date.today() + timedelta(days=30)
        result = parse_weather_response(open_meteo_response, far_future)
        assert result is None

    def test_accepts_date_string(self, open_meteo_response):
        today_str = date.today().isoformat()
        result = parse_weather_response(open_meteo_response, today_str)
        assert result is not None
        assert result["temperature_max"] == 18.5

    def test_returns_none_for_empty_response(self):
        result = parse_weather_response({}, date.today())
        assert result is None


class TestGetCoordinatesForDay:
    def test_returns_first_event_coordinates(
        self, trip_factory, user_factory, event_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        event = event_factory(day=day)
        result = get_coordinates_for_day(day)
        assert result == (event.latitude, event.longitude)

    def test_skips_event_without_coordinates(
        self, trip_factory, user_factory, event_factory, stay_factory
    ):
        """Event with cleared coords → falls back to stay. Use queryset update to bypass model geocoding."""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        event = event_factory(day=day)
        Event.objects.filter(pk=event.pk).update(latitude=None, longitude=None)
        stay = stay_factory()
        day.stay = stay
        day.save()
        result = get_coordinates_for_day(day)
        assert result == (stay.latitude, stay.longitude)

    def test_falls_back_to_stay_when_no_events(
        self, trip_factory, user_factory, stay_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        stay = stay_factory()
        day.stay = stay
        day.save()
        result = get_coordinates_for_day(day)
        assert result == (stay.latitude, stay.longitude)

    def test_returns_none_when_no_coordinates_available(
        self, trip_factory, user_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        result = get_coordinates_for_day(day)
        assert result is None

    def test_returns_none_when_stay_has_no_coordinates(
        self, trip_factory, user_factory, stay_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        stay = stay_factory()
        Stay.objects.filter(pk=stay.pk).update(latitude=None, longitude=None)
        stay.refresh_from_db()
        day.stay = stay
        day.save()
        result = get_coordinates_for_day(day)
        assert result is None
