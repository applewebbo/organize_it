import pytest

from tests.trips.factories import EventFactory, StayFactory, TripFactory
from trips.templatetags.trip_tags import (
    event_bg_color,
    event_border_color,
    event_icon,
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
    """Fixture that creates a trip with multiple stays"""
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


class TestDayNavigation:
    """Tests for day navigation template tags"""

    def test_next_day_returns_correct_day(self, trip_with_stays):
        """Test next_day returns the correct following day"""
        days = list(trip_with_stays.days.all())
        assert next_day(days[0]) == days[1]
        assert next_day(days[1]) == days[2]
        assert next_day(days[-1]) is None

    def test_next_day_with_invalid_day(self, trip_with_stays):
        """Test next_day with day not in trip"""
        other_trip = TripFactory()
        other_day = other_trip.days.first()
        other_day.trip = trip_with_stays
        assert next_day(other_day) is None
        other_day.trip = other_trip

    def test_is_last_day_identification(self, trip_with_stays):
        """Test is_last_day correctly identifies last day"""
        days = list(trip_with_stays.days.all())
        assert not is_last_day(days[0])
        assert not is_last_day(days[1])
        assert is_last_day(days[-1])

    def test_is_last_day_with_no_trip(self, trip_with_stays):
        """Test is_last_day returns False when day has no trip"""
        day = trip_with_stays.days.first()
        day.trip = None
        assert not is_last_day(day)

    def test_is_first_day_of_trip(self, trip_with_stays):
        """Test is_first_day_of_trip correctly identifies first day of trip"""
        days = list(trip_with_stays.days.all())

        # First day should return True
        assert is_first_day_of_trip(days[0])

        # Other days should return False
        assert not is_first_day_of_trip(days[1])
        assert not is_first_day_of_trip(days[2])

        # Test with day from another trip (should be first day of its own trip)
        other_trip = TripFactory()
        other_day = other_trip.days.first()
        assert is_first_day_of_trip(
            other_day
        )  # Should be True for first day of any trip

        # Test with day that has no trip
        other_day.trip = None
        assert not is_first_day_of_trip(other_day)


class TestStayChecks:
    """Tests for stay-related template tags"""

    def test_has_different_stay_comparison(self, trip_with_stays):
        """Test has_different_stay correctly compares stays"""
        days = list(trip_with_stays.days.all())
        assert not has_different_stay(days[0], days[1])
        assert has_different_stay(days[1], days[2])
        assert has_different_stay(days[-1], None)

    @pytest.mark.parametrize(
        "day_index,expected",
        [
            (0, True),  # First day of first stay
            (1, False),  # Second day of first stay
            (2, True),  # First day of second stay
        ],
    )
    def test_is_first_day_of_stay(self, trip_with_stays, day_index, expected):
        """Test is_first_day_of_stay correctly identifies first days"""
        days = list(trip_with_stays.days.all())
        assert is_first_day_of_stay(days[day_index]) == expected

    def test_is_first_day_of_stay_without_stay(self, trip_with_stays):
        """Test is_first_day_of_stay returns False when day has no stay"""
        day = trip_with_stays.days.first()
        day.stay = None
        assert not is_first_day_of_stay(day)


class TestEventFormatting:
    """Tests for event-related template tags"""

    @pytest.mark.parametrize(
        "category,expected_icon",
        [
            (1, "car-profile"),
            (2, "images"),
            (3, "fork-knife"),
            (99, "question-mark-circle"),
        ],
    )
    def test_event_icon(self, category, expected_icon):
        """Test event_icon returns correct icon for each category"""
        event = EventFactory(category=category)
        assert event_icon(event) == expected_icon

    @pytest.mark.parametrize(
        "category,expected_class",
        [
            (1, "bg-tr-blue-100 dark:bg-tr-blue-100/30"),
            (2, "bg-exp-green-100 dark:bg-exp-green-100/30"),
            (3, "bg-meal-yellow-100 dark:bg-meal-yellow-100/30"),
            (99, "bg-gray-100"),
        ],
    )
    def test_event_bg_color(self, category, expected_class):
        """Test event_bg_color returns correct background color"""
        event = EventFactory(category=category)
        assert event_bg_color(event) == expected_class

    @pytest.mark.parametrize(
        "category,expected_class",
        [
            (1, "border-tr-blue-300 dark:border-tr-blue-700"),
            (2, "border-exp-green-300 dark:border-exp-green-700"),
            (3, "border-meal-yellow-300 dark:border-meal-yellow-700"),
            (99, "border-gray-300"),
        ],
    )
    def test_event_border_color(self, category, expected_class):
        """Test event_border_color returns correct border color"""
        event = EventFactory(category=category)
        assert event_border_color(event) == expected_class


class TestPhoneFormat:
    """Tests for phone number formatting"""

    @pytest.mark.parametrize(
        "phone_number,expected",
        [
            ("+1234567890", "+12 345 67890"),
            ("1234567890", "+39 1234567890"),
            ("+39 123 456 7890", "+39 1234567890"),
            ("", ""),
            (None, None),
            ("123", "+39 123"),
            ("1234567890123456", "+39 1234567890123456"),
        ],
    )
    def test_phone_format_various_inputs(self, phone_number, expected):
        """Test phone_format handles various input formats correctly"""
        assert phone_format(phone_number) == expected

    @pytest.mark.parametrize(
        "prefix,number,expected",
        [
            ("02", "1234567", "+39 02 1234567"),
            ("0861", "1234567", "+39 0861 1234567"),
            ("06", "1234567", "+39 06 1234567"),
        ],
    )
    def test_phone_format_italian_prefixes(self, prefix, number, expected):
        """Test phone_format handles Italian prefixes correctly"""
        full_number = f"{prefix}{number}"
        assert phone_format(full_number) == expected
