import pytest

from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.templatetags.trip_tags import (
    event_bg_color,
    event_border_color,
    event_icon,
    event_icon_color,
    event_type_icon,
    format_duration,
    format_opening_hours,
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
            (2, "border-exp-green-300 dark:border-exp-green-700"),
            (3, "border-meal-yellow-300 dark:border-meal-yellow-700"),
            (99, "border-gray-300"),
        ],
    )
    def test_event_border_color(self, category, expected_class):
        """Test event_border_color returns correct border color"""
        event = EventFactory(category=category)
        assert event_border_color(event) == expected_class

    @pytest.mark.parametrize(
        "category,expected_class",
        [
            (2, "text-exp-green-700 dark:text-exp-green-300"),
            (3, "text-meal-yellow-700 dark:text-meal-yellow-300"),
            (99, "text-base-content"),
        ],
    )
    def test_event_icon_color(self, category, expected_class):
        """Test event_icon_color returns correct icon color"""
        event = EventFactory(category=category)
        assert event_icon_color(event) == expected_class

    @pytest.mark.parametrize(
        "event_type,expected_icon",
        [
            (1, "ph-bank"),  # MUSEUM
            (2, "ph-tree"),  # PARK
            (3, "ph-person-simple-walk"),  # WALK
            (4, "ph-barbell"),  # SPORT
            (5, "ph-question"),  # OTHER
        ],
    )
    def test_event_type_icon_experience(self, event_type, expected_icon):
        """Test event_type_icon returns correct icon for experience types"""
        trip = TripFactory()
        experience = ExperienceFactory(trip=trip, type=event_type)
        assert event_type_icon(experience) == expected_icon

    @pytest.mark.parametrize(
        "event_type,expected_icon",
        [
            (1, "ph-coffee"),  # BREAKFAST
            (2, "ph-fork-knife"),  # LUNCH
            (3, "ph-wine"),  # DINNER
            (4, "ph-cookie"),  # SNACK
        ],
    )
    def test_event_type_icon_meal(self, event_type, expected_icon):
        """Test event_type_icon returns correct icon for meal types"""
        trip = TripFactory()
        meal = MealFactory(trip=trip, type=event_type)
        assert event_type_icon(meal) == expected_icon

    def test_event_type_icon_unknown_category(self):
        """Test event_type_icon returns default icon for unknown category"""
        event = EventFactory(category=99)
        assert event_type_icon(event) == "ph-question"

    def test_event_type_icon_unknown_experience_type(self):
        """Test event_type_icon returns default icon for unknown experience type"""
        trip = TripFactory()
        experience = ExperienceFactory(trip=trip, type=99)
        assert event_type_icon(experience) == "ph-question"

    def test_event_type_icon_unknown_meal_type(self):
        """Test event_type_icon returns default icon for unknown meal type"""
        trip = TripFactory()
        meal = MealFactory(trip=trip, type=99)
        assert event_type_icon(meal) == "ph-fork-knife"


class TestFormatDuration:
    """Tests for format_duration template tag"""

    def test_format_duration_none(self):
        """Test format_duration with None input"""
        assert format_duration(None) == ""

    def test_format_duration_with_days(self):
        """Test format_duration with days"""
        from datetime import timedelta

        duration = timedelta(days=2, hours=3, minutes=30)
        assert format_duration(duration) == "2d 3h 30m"

    def test_format_duration_hours_only(self):
        """Test format_duration with hours and minutes, no days"""
        from datetime import timedelta

        duration = timedelta(hours=5, minutes=45)
        assert format_duration(duration) == "5h 45m"

    def test_format_duration_minutes_only(self):
        """Test format_duration with only minutes"""
        from datetime import timedelta

        duration = timedelta(minutes=30)
        assert format_duration(duration) == "30m"

    def test_format_duration_zero_minutes(self):
        """Test format_duration with zero minutes (hours only)"""
        from datetime import timedelta

        duration = timedelta(hours=2)
        assert format_duration(duration) == "2h"

    def test_format_duration_zero_hours(self):
        """Test format_duration with zero hours (days and minutes)"""
        from datetime import timedelta

        duration = timedelta(days=1, minutes=15)
        assert format_duration(duration) == "1d 15m"

    def test_format_duration_less_than_minute(self):
        """Test format_duration with less than a minute (shows as 0m)"""
        from datetime import timedelta

        duration = timedelta(seconds=45)
        assert format_duration(duration) == "0m"


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


class TestFormatOpeningHours:
    """Tests for format_opening_hours template tag"""

    def test_empty_input(self):
        """Test with empty dictionary input"""
        assert format_opening_hours({}) == ""

    def test_invalid_input_type(self):
        """Test with invalid input type (not a dictionary)"""
        assert format_opening_hours(None) == ""
        assert format_opening_hours("string") == ""
        assert format_opening_hours([]) == ""

    def test_all_days_same_hours(self):
        """Test when all days have the same opening hours"""
        hours_data = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "09:00", "close": "17:00"},
            "wednesday": {"open": "09:00", "close": "17:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
            "friday": {"open": "09:00", "close": "17:00"},
            "saturday": {"open": "09:00", "close": "17:00"},
            "sunday": {"open": "09:00", "close": "17:00"},
        }
        expected = (
            '<ul class="list-none p-0 m-0 leading-normal">'
            "<li><strong>Lun-Dom:</strong> 09:00 – 17:00</li>"
            "</ul>"
        )
        assert format_opening_hours(hours_data) == expected

    def test_some_days_closed(self):
        """Test when some days are closed"""
        hours_data = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "09:00", "close": "17:00"},
            "wednesday": {"open": "09:00", "close": "17:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
            "friday": {"open": "09:00", "close": "17:00"},
            "saturday": {"open": "10:00", "close": "14:00"},
            "sunday": {},  # Closed
        }
        expected = (
            '<ul class="list-none p-0 m-0 leading-normal">'
            "<li><strong>Lun-Ven:</strong> 09:00 – 17:00</li>"
            "<li><strong>Sab:</strong> 10:00 – 14:00</li>"
            "<li><strong>Dom:</strong> Chiuso</li>"
            "</ul>"
        )
        assert format_opening_hours(hours_data) == expected

    def test_complex_schedule(self):
        """Test with a more complex opening hours schedule"""
        hours_data = {
            "monday": {"open": "09:00", "close": "13:00"},
            "tuesday": {"open": "09:00", "close": "13:00"},
            "wednesday": {"open": "14:00", "close": "18:00"},
            "thursday": {"open": "09:00", "close": "13:00"},
            "friday": {"open": "09:00", "close": "13:00"},
            "saturday": {"open": "10:00", "close": "14:00"},
            "sunday": {"open": "10:00", "close": "14:00"},
        }
        expected = (
            '<ul class="list-none p-0 m-0 leading-normal">'
            "<li><strong>Lun-Mar:</strong> 09:00 – 13:00</li>"
            "<li><strong>Mer:</strong> 14:00 – 18:00</li>"
            "<li><strong>Gio-Ven:</strong> 09:00 – 13:00</li>"
            "<li><strong>Sab-Dom:</strong> 10:00 – 14:00</li>"
            "</ul>"
        )
        assert format_opening_hours(hours_data) == expected

    def test_missing_open_close_keys(self):
        """Test with missing 'open' or 'close' keys for a day"""
        hours_data = {
            "monday": {"open": "09:00"},  # Missing close
            "tuesday": {"close": "17:00"},  # Missing open
            "wednesday": {},  # Both missing
            "thursday": {"open": "09:00", "close": "17:00"},
        }
        expected = (
            '<ul class="list-none p-0 m-0 leading-normal">'
            "<li><strong>Lun-Mer:</strong> Chiuso</li>"
            "<li><strong>Gio:</strong> 09:00 – 17:00</li>"
            "<li><strong>Ven-Dom:</strong> Chiuso</li>"
            "</ul>"
        )
        assert format_opening_hours(hours_data) == expected

    def test_empty_hours_data_for_day(self):
        """Test with empty hours data for a specific day"""
        hours_data = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {},
            "wednesday": {"open": "09:00", "close": "17:00"},
        }
        expected = (
            '<ul class="list-none p-0 m-0 leading-normal">'
            "<li><strong>Lun:</strong> 09:00 – 17:00</li>"
            "<li><strong>Mar:</strong> Chiuso</li>"
            "<li><strong>Mer:</strong> 09:00 – 17:00</li>"
            "<li><strong>Gio-Dom:</strong> Chiuso</li>"
            "</ul>"
        )
        assert format_opening_hours(hours_data) == expected
