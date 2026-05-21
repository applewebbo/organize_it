import pytest

from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.templatetags.trip_tags import (
    dict_get,
    duration_display,
    event_bg_color,
    event_border_color,
    event_icon,
    event_icon_color,
    event_type_icon,
    format_duration,
    format_minutes,
    format_opening_hours,
    format_opening_hours_text,
    has_different_stay,
    is_first_day_of_stay,
    is_first_day_of_trip,
    is_last_day,
    meal_type_label,
    next_day,
    phone_format,
    prev_day,
    stay_transfer_in,
    stay_transfer_out,
    user_display_name,
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

    def test_prev_day_returns_correct_day(self, trip_with_stays):
        """Test prev_day returns the correct previous day"""
        days = list(trip_with_stays.days.all())
        assert prev_day(days[0]) is None
        assert prev_day(days[1]) == days[0]
        assert prev_day(days[2]) == days[1]

    def test_prev_day_with_invalid_day(self, trip_with_stays):
        """Test prev_day with day not in trip"""
        other_trip = TripFactory()
        other_day = other_trip.days.first()
        other_day.trip = trip_with_stays
        assert prev_day(other_day) is None
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


class TestFormatOpeningHoursText:
    """Tests for format_opening_hours_text template filter (plain-text PDF version)"""

    def test_empty_input(self):
        assert format_opening_hours_text({}) == ""

    def test_invalid_input_type(self):
        assert format_opening_hours_text(None) == ""
        assert format_opening_hours_text("string") == ""

    def test_all_days_same_hours(self):
        hours_data = {
            day: {"open": "09:00", "close": "17:00"}
            for day in [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]
        }
        assert format_opening_hours_text(hours_data) == "Lun-Dom: 09:00 – 17:00"

    def test_some_days_closed(self):
        hours_data = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "09:00", "close": "17:00"},
            "wednesday": {"open": "09:00", "close": "17:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
            "friday": {"open": "09:00", "close": "17:00"},
            "saturday": {"open": "10:00", "close": "14:00"},
            "sunday": {},
        }
        result = format_opening_hours_text(hours_data)
        assert "Lun-Ven: 09:00 – 17:00" in result
        assert "Sab: 10:00 – 14:00" in result
        assert "Dom: Chiuso" in result

    def test_missing_open_close_keys(self):
        hours_data = {
            "monday": {"open": "09:00"},
            "tuesday": {"close": "17:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
        }
        result = format_opening_hours_text(hours_data)
        assert "Gio: 09:00 – 17:00" in result

    def test_separator_between_groups(self):
        hours_data = {
            "monday": {"open": "09:00", "close": "13:00"},
            "tuesday": {"open": "14:00", "close": "18:00"},
        }
        result = format_opening_hours_text(hours_data)
        assert " · " in result


class TestStayTransferTags:
    """Tests for stay transfer template tags"""

    def test_stay_transfer_out_no_stay(self):
        """Test stay_transfer_out returns None when day has no stay"""
        trip = TripFactory()
        day = trip.days.first()
        day.stay = None
        assert stay_transfer_out(day) is None

    def test_stay_transfer_out_not_last_day_of_stay(self):
        """Test stay_transfer_out returns None when not last day of multi-day stay"""
        from trips.models import StayTransfer

        trip = TripFactory()
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        # Set same stay for first two days
        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay1
        days[1].save()
        days[2].stay = stay2
        days[2].save()

        # Create a transfer from stay1 to stay2
        StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="driving"
        )

        # First day should return None (not last day of stay)
        assert stay_transfer_out(days[0]) is None

    def test_stay_transfer_out_last_day_of_stay(self):
        """Test stay_transfer_out returns transfer on last day of stay"""
        from trips.models import StayTransfer

        trip = TripFactory()
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        # Set same stay for first two days
        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay1
        days[1].save()
        days[2].stay = stay2
        days[2].save()

        # Create a transfer from stay1 to stay2
        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="driving"
        )

        # Second day (last day of stay1) should return the transfer
        assert stay_transfer_out(days[1]) == transfer

    def test_stay_transfer_out_no_transfer(self):
        """Test stay_transfer_out returns None when last day of stay but no transfer exists"""
        trip = TripFactory()
        days = list(trip.days.all())
        stay = StayFactory()

        days[0].stay = stay
        days[0].save()
        # No StayTransfer created
        assert stay_transfer_out(days[0]) is None

    def test_stay_transfer_in_no_stay(self):
        """Test stay_transfer_in returns None when day has no stay"""
        trip = TripFactory()
        day = trip.days.first()
        day.stay = None
        assert stay_transfer_in(day) is None

    def test_stay_transfer_in_with_transfer(self):
        """Test stay_transfer_in returns transfer when exists"""
        from trips.models import StayTransfer

        trip = TripFactory()
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        # Create a transfer from stay1 to stay2
        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="driving"
        )

        # Day with stay2 should return the transfer
        assert stay_transfer_in(days[1]) == transfer

    def test_stay_transfer_in_no_transfer(self):
        """Test stay_transfer_in returns None when no transfer exists"""
        trip = TripFactory()
        days = list(trip.days.all())
        stay = StayFactory()

        days[0].stay = stay
        days[0].save()

        # No transfer created
        assert stay_transfer_in(days[0]) is None


class TestIsLastDayEdgeCases:
    """Additional edge case tests for is_last_day"""

    def test_is_last_day_day_not_in_trip_days(self):
        """Test is_last_day returns False when day is not in trip's days list"""
        trip1 = TripFactory()
        trip2 = TripFactory()

        # Get a day from trip2
        day = trip2.days.first()

        # Temporarily change its trip reference without actually being in trip1's days
        original_trip = day.trip
        day.trip = trip1

        # This should return False because day is not in trip1's days.all()
        result = is_last_day(day)

        # Restore
        day.trip = original_trip

        assert result is False


class TestWeatherTags:
    pytestmark = pytest.mark.django_db

    def test_weather_widget_with_data(self, trip_factory, user_factory):
        from django.template import Context, Template

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        day.weather_data = {
            "temperature_max": 22.0,
            "temperature_min": 12.0,
            "precipitation_sum": 0.0,
            "wind_speed_max": 15.0,
            "weather_code": 0,
            "weather_icon": "ph-sun",
            "weather_label": "Clear sky",
        }
        day.save()
        t = Template("{% load trip_tags %}{% weather_widget day %}")
        result = t.render(Context({"day": day}))
        assert "22" in result
        assert "ph-sun" in result

    def test_weather_widget_without_data(self, trip_factory, user_factory):
        from django.template import Context, Template

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        t = Template("{% load trip_tags %}{% weather_widget day %}")
        result = t.render(Context({"day": day}))
        assert "Forecast unavailable" in result

    def test_weather_summary_with_data(self, trip_factory, user_factory):
        from django.template import Context, Template

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        day.weather_data = {
            "weather_icon": "ph-sun",
            "temperature_max": 22.0,
            "temperature_min": 12.0,
        }
        day.save()
        t = Template("{% load trip_tags %}{% weather_summary trip %}")
        result = t.render(Context({"trip": trip}))
        assert "ph-sun" in result

    def test_weather_summary_without_data(self, trip_factory, user_factory):
        from django.template import Context, Template

        user = user_factory()
        trip = trip_factory(author=user)
        t = Template("{% load trip_tags %}{% weather_summary trip %}")
        result = t.render(Context({"trip": trip}))
        # No weather data → nothing rendered
        assert "ph-" not in result

    def test_trip_day_one_weather_with_data(self, trip_factory, user_factory):
        from django.template import Context, Template

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.order_by("number").first()
        day.weather_data = {"weather_icon": "ph-sun", "temperature_max": 20.0}
        day.save()
        t = Template(
            "{% load trip_tags %}{% trip_day_one_weather trip as w %}{{ w.weather_icon }}"
        )
        result = t.render(Context({"trip": trip}))
        assert "ph-sun" in result

    def test_trip_day_one_weather_no_days(self, user_factory):
        from django.template import Context, Template

        from trips.models import Trip

        user = user_factory()
        trip = Trip.objects.create(
            author=user,
            title="No Days Trip",
            destination="Nowhere",
            start_date=None,
            end_date=None,
        )
        t = Template("{% load trip_tags %}{% trip_day_one_weather trip as w %}{{ w }}")
        result = t.render(Context({"trip": trip}))
        assert result.strip() == "None"


class TestDictGet:
    def test_existing_key(self):
        assert dict_get({"a": 1, "b": 2}, "a") == 1

    def test_missing_key(self):
        assert dict_get({"a": 1}, "z") is None

    def test_none_dict(self):
        assert dict_get(None, "x") is None


class TestUserDisplayName:
    def test_profile_first_name_takes_precedence(self, user_factory):
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()
        assert user_display_name(user) == "John"

    def test_email_prefix_when_no_profile_first_name(self, user_factory):
        user = user_factory()
        user.profile.first_name = ""
        user.profile.save()
        assert user_display_name(user) == user.email.split("@")[0]

    def test_none_user_returns_empty(self):
        assert user_display_name(None) == ""


class TestDurationDisplay:
    def test_none_returns_empty(self):

        assert duration_display(None) == ""

    def test_zero_returns_empty(self):
        from datetime import timedelta

        assert duration_display(timedelta(0)) == ""

    def test_minutes_only(self):
        from datetime import timedelta

        assert duration_display(timedelta(minutes=45)) == "45min"

    def test_hours_only(self):
        from datetime import timedelta

        assert duration_display(timedelta(hours=2)) == "2h"

    def test_hours_and_minutes(self):
        from datetime import timedelta

        assert duration_display(timedelta(hours=1, minutes=30)) == "1h 30min"


class TestMealTypeLabel:
    def test_returns_empty_for_experience(self):
        trip = TripFactory()
        day = trip.days.first()
        event = ExperienceFactory(day=day)
        assert meal_type_label(event) == ""

    def test_returns_empty_for_undefined(self):
        from trips.models import Meal

        trip = TripFactory()
        day = trip.days.first()
        event = MealFactory(day=day, type=Meal.Type.UNDEFINED)
        assert meal_type_label(event) == ""

    def test_returns_label_for_defined_type(self):
        from trips.models import Meal

        trip = TripFactory()
        day = trip.days.first()
        event = MealFactory(day=day, type=Meal.Type.DINNER)
        assert meal_type_label(event) == "Dinner"

    def test_returns_label_via_event_queryset(self):
        """Test that meal_type_label works when called with base Event instance."""
        from trips.models import Event, Meal

        trip = TripFactory()
        day = trip.days.first()
        MealFactory(day=day, type=Meal.Type.LUNCH)
        event = Event.objects.get(day=day)
        assert meal_type_label(event) == "Lunch"


class TestFormatMinutes:
    def test_none_returns_empty(self):
        assert format_minutes(None) == ""

    def test_hours_and_minutes(self):
        assert format_minutes(150) == "2h 30min"

    def test_hours_only(self):
        assert format_minutes(120) == "2h"

    def test_minutes_only(self):
        assert format_minutes(45) == "45min"

    def test_zero(self):
        assert format_minutes(0) == "0min"
