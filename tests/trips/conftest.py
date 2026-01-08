"""Trips app test fixtures and configuration"""

import pytest


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
