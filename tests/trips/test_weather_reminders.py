import datetime

import pytest
from django.utils import timezone

from trips.models import Day
from trips.tasks import send_weather_reminders

pytestmark = pytest.mark.django_db


@pytest.fixture
def today():
    return timezone.now().date()


@pytest.fixture
def target_date(today):
    return today + datetime.timedelta(days=3)


def test_send_weather_reminders_sends_email(
    trip_factory, today, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    # create days with weather data
    Day.objects.create(
        trip=trip,
        number=1,
        date=target_date,
        weather_data={"temperature_2m_max": 25, "temperature_2m_min": 15},
    )
    Day.objects.create(
        trip=trip,
        number=2,
        date=target_date + datetime.timedelta(days=1),
        weather_data={"temperature_2m_max": 24, "temperature_2m_min": 14},
    )

    result = send_weather_reminders()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f"Weather Forecast for your trip: {trip.title}"
    assert "25" in mailoutbox[0].body
    assert "15" in mailoutbox[0].body

    # Check that weather_reminder_sent_at was updated
    trip.refresh_from_db()
    assert trip.weather_reminder_sent_at == today


def test_send_weather_reminders_wrong_date(
    trip_factory, today, target_date, mailoutbox
):
    # trip starting in 4 days
    trip_factory(start_date=target_date + datetime.timedelta(days=1))
    # trip starting in 2 days
    trip_factory(start_date=target_date - datetime.timedelta(days=1))

    result = send_weather_reminders()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_weather_reminders_already_sent(
    trip_factory, today, target_date, mailoutbox
):
    trip_factory(start_date=target_date, weather_reminder_sent_at=today)

    result = send_weather_reminders()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_weather_reminders_no_weather_data(
    trip_factory, today, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    # day without weather_data
    Day.objects.create(trip=trip, number=1, date=target_date, weather_data=None)

    send_weather_reminders()

    # Mail is skipped because no weather data exists
    assert len(mailoutbox) == 0


def test_send_weather_reminders_user_opt_out(
    trip_factory, today, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    trip.author.profile.show_weather = False
    trip.author.profile.save()

    Day.objects.create(
        trip=trip,
        number=1,
        date=target_date,
        weather_data={"temperature_2m_max": 25, "temperature_2m_min": 15},
    )

    result = send_weather_reminders()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0
