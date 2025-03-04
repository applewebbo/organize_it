import pytest

from tests.trips.factories import StayFactory, TripFactory
from trips.templatetags.trip_tags import has_different_stay, is_last_day, next_day

pytestmark = pytest.mark.django_db


@pytest.fixture
def trip_with_stays():
    trip = TripFactory()
    stay1 = StayFactory()
    stay2 = StayFactory()

    # Get all days from the trip
    days = list(trip.days.all())

    # Set first two days to stay1
    days[0].stay = stay1
    days[0].save()
    days[1].stay = stay1
    days[1].save()

    # Set last two days to stay2
    days[2].stay = stay2
    days[2].save()
    if len(days) > 3:
        days[3].stay = stay2
        days[3].save()

    return trip


def test_next_day(trip_with_stays):
    """Test next_day template filter"""
    days = list(trip_with_stays.days.all())

    # Test first day returns second day
    assert next_day(days[0]) == days[1]

    # Test middle day returns next day
    assert next_day(days[1]) == days[2]

    # Test last day returns None
    assert next_day(days[-1]) is None


def test_next_day_value_error(trip_with_stays):
    """Test next_day template filter with a day not in the trip"""
    # Create a day that doesn't belong to the trip
    other_trip = TripFactory()
    other_day = other_trip.days.first()

    # Change the day's trip without changing its position in days list
    original_trip = other_day.trip
    other_day.trip = trip_with_stays

    # Should return None when day is not found in trip's days
    # (day belongs to other_trip's days list but claims to be in trip_with_stays)
    assert next_day(other_day) is None

    # Restore the original trip to avoid database inconsistencies
    other_day.trip = original_trip


def test_next_day_index_error():
    """Test next_day template filter with an empty trip"""
    # Create a trip and clear its days
    empty_trip = TripFactory()
    empty_trip.days.all().delete()

    # Create a test day from another trip
    other_trip = TripFactory()
    test_day = other_trip.days.first()
    test_day.trip = empty_trip

    # Should return None when trip has no days
    assert next_day(test_day) is None


def test_is_last_day(trip_with_stays):
    """Test is_last_day template filter"""
    days = list(trip_with_stays.days.all())

    # Test first day is not last
    assert not is_last_day(days[0])

    # Test middle day is not last
    assert not is_last_day(days[1])

    # Test last day is last
    assert is_last_day(days[-1])


def test_is_last_day_value_error(trip_with_stays):
    """Test is_last_day template filter with a day not in the trip"""
    # Create a day that doesn't belong to the trip
    other_trip = TripFactory()
    other_day = other_trip.days.first()

    # Change the day's trip without changing its position in days list
    original_trip = other_day.trip
    other_day.trip = trip_with_stays

    # Should return False when day is not found in trip's days
    # (day belongs to other_trip's days list but claims to be in trip_with_stays)
    assert not is_last_day(other_day)

    # Restore the original trip to avoid database inconsistencies
    other_day.trip = original_trip


def test_is_last_day_index_error():
    """Test is_last_day template filter with an empty trip"""
    # Create a trip and clear its days
    empty_trip = TripFactory()
    empty_trip.days.all().delete()

    # Create a test day from another trip
    other_trip = TripFactory()
    test_day = other_trip.days.first()
    test_day.trip = empty_trip

    # Should return False when trip has no days
    assert not is_last_day(test_day)


def test_has_different_stay(trip_with_stays):
    """Test has_different_stay template filter"""
    days = list(trip_with_stays.days.all())

    # Test same stay returns False
    assert not has_different_stay(days[0], days[1])

    # Test different stays returns True
    assert has_different_stay(days[1], days[2])

    # Test with None returns True
    assert has_different_stay(days[-1], None)
