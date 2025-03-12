import pytest

from tests.trips.factories import EventFactory, StayFactory, TripFactory
from trips.templatetags.trip_tags import (
    event_bg_color,  # Add these
    event_border_color,  # new
    event_icon,
    event_icon_color,  # imports
    has_different_stay,
    is_first_day_of_stay,
    is_first_day_of_trip,
    is_last_day,
    next_day,
    phone_format,
)

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


def test_trip_with_stays_fixture(trip_with_stays):
    """Test that trip_with_stays fixture creates correct setup"""
    days = list(trip_with_stays.days.all())

    # Verify we have at least 3 days
    assert len(days) >= 3

    # First two days should have same stay
    assert days[0].stay == days[1].stay

    # Last days should have different stay from first days
    assert days[0].stay != days[2].stay
    assert days[1].stay != days[2].stay

    # If there's a fourth day, it should have same stay as third day
    if len(days) > 3:
        assert days[2].stay == days[3].stay


def test_trip_with_stays_stays_exist(trip_with_stays):
    """Test that stays in trip_with_stays are properly created"""
    days = list(trip_with_stays.days.all())

    # Verify stays are not None
    assert days[0].stay is not None
    assert days[1].stay is not None
    assert days[2].stay is not None


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


def test_is_first_day_of_stay(trip_with_stays):
    """Test is_first_day_of_stay template filter"""
    days = list(trip_with_stays.days.all())

    # First day of first stay should return True
    assert is_first_day_of_stay(days[0])

    # Second day of first stay should return False
    assert not is_first_day_of_stay(days[1])

    # First day of second stay should return True
    assert is_first_day_of_stay(days[2])

    # Test with day without stay
    days[0].stay = None
    assert not is_first_day_of_stay(days[0])


def test_is_first_day_of_trip(trip_with_stays):
    """Test is_first_day_of_trip template filter"""
    days = list(trip_with_stays.days.all())

    # First day should return True
    assert is_first_day_of_trip(days[0])

    # Other days should return False
    assert not is_first_day_of_trip(days[1])
    assert not is_first_day_of_trip(days[2])


def test_event_icon():
    """Test event_icon template filter"""
    # Test all event categories
    transport = EventFactory(category=1)
    assert event_icon(transport) == "truck"

    experience = EventFactory(category=2)
    assert event_icon(experience) == "photo"

    meal = EventFactory(category=3)
    assert event_icon(meal) == "cake"

    # Test unknown category
    unknown = EventFactory(category=99)
    assert event_icon(unknown) == "question-mark-circle"


def test_event_bg_color():
    """Test event_bg_color template filter"""
    # Test all event categories
    transport = EventFactory(category=1)
    assert event_bg_color(transport) == "bg-[#BAEAFF]"

    experience = EventFactory(category=2)
    assert event_bg_color(experience) == "bg-[#DDFFCF]"

    meal = EventFactory(category=3)
    assert event_bg_color(meal) == "bg-[#FFF4D4]"

    # Test unknown category
    unknown = EventFactory(category=99)
    assert event_bg_color(unknown) == "bg-gray-300"


def test_event_border_color():
    """Test event_border_color template filter"""
    # Test all event categories
    transport = EventFactory(category=1)
    assert event_border_color(transport) == "border-[#5ECEFF]"

    experience = EventFactory(category=2)
    assert event_border_color(experience) == "border-[#98F56F]"

    meal = EventFactory(category=3)
    assert event_border_color(meal) == "border-[#FFDB6D]"

    # Test unknown category
    unknown = EventFactory(category=99)
    assert event_border_color(unknown) == "bg-gray-300"


def test_event_icon_color():
    """Test event_icon_color template filter"""
    # Test all event categories
    transport = EventFactory(category=1)
    assert event_icon_color(transport) == "text-transport-blue"

    experience = EventFactory(category=2)
    assert event_icon_color(experience) == "text-experience-green"

    meal = EventFactory(category=3)
    assert event_icon_color(meal) == "text-meal-yellow"

    # Test unknown category
    unknown = EventFactory(category=99)
    assert event_icon_color(unknown) == "text-base-content"


@pytest.mark.parametrize(
    "phone_number,expected",
    [
        ("+1234567890", "+12 345 67890"),  # Adjusted spacing
        ("1234567890", "+39 1234567890"),  # Italian prefix is added
        ("+39 123 456 7890", "+39 1234567890"),  # Spaces are removed
        ("", ""),  # Empty string remains empty
        (None, None),  # None remains None
        ("123", "+39 123"),  # Short numbers get prefix
        ("1234567890123456", "+39 1234567890123456"),  # Long numbers get prefix
    ],
)
def test_phone_format(phone_number, expected):
    assert phone_format(phone_number) == expected
