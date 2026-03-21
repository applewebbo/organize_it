"""Trips app test fixtures and configuration"""

from datetime import date, timedelta

import pytest


@pytest.fixture
def open_meteo_response():
    """Generate a realistic Open-Meteo daily response with dates relative to today."""
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]
    return {
        "latitude": 41.9,
        "longitude": 12.5,
        "timezone": "Europe/Rome",
        "daily_units": {
            "time": "iso8601",
            "weather_code": "wmo code",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "wind_speed_10m_max": "km/h",
        },
        "daily": {
            "time": [d.isoformat() for d in days],
            "weather_code": [0, 1, 3, 61, 63, 80, 95],
            "temperature_2m_max": [18.5, 17.2, 15.0, 12.3, 11.8, 14.0, 16.5],
            "temperature_2m_min": [8.1, 7.5, 9.2, 10.0, 8.5, 7.0, 6.8],
            "precipitation_sum": [0.0, 0.0, 0.5, 8.2, 12.5, 4.1, 0.0],
            "wind_speed_10m_max": [12.0, 15.3, 22.1, 35.0, 28.5, 18.2, 10.5],
        },
    }


@pytest.fixture
def authenticated_user(client, user_factory):
    """Create and login a user, return (user, client) tuple."""
    user = user_factory()
    client.force_login(user)
    return user, client


@pytest.fixture
def trip_with_days(user_factory, trip_factory):
    """Create a trip with user and pre-generated days."""
    user = user_factory()
    trip = trip_factory(author=user)
    return trip, user


@pytest.fixture
def trip_day_event(user_factory, trip_factory, event_factory):
    """Create complete trip->day->event hierarchy."""
    user = user_factory()
    trip = trip_factory(author=user)
    day = trip.days.first()
    event = event_factory(day=day)
    return trip, day, event, user
