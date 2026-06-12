import datetime

import pytest
from allauth.account.models import EmailAddress
from django.utils import timezone

from trips.models import Day, TripCollaboration
from trips.tasks import send_weather_reminders

pytestmark = pytest.mark.django_db


def _day_with_weather(trip, date):
    return Day.objects.create(
        trip=trip,
        number=1,
        date=date,
        weather_data={"temperature_max": 25, "temperature_min": 15},
    )


def _add_collaborator(trip, user, owner):
    return TripCollaboration.objects.create(
        trip=trip, user=user, color="blue", added_by=owner
    )


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
    trip.author.profile.language = "en"
    trip.author.profile.save()
    # create days with weather data
    Day.objects.create(
        trip=trip,
        number=1,
        date=target_date,
        weather_data={"temperature_max": 25, "temperature_min": 15},
    )
    Day.objects.create(
        trip=trip,
        number=2,
        date=target_date + datetime.timedelta(days=1),
        weather_data={"temperature_max": 24, "temperature_min": 14},
    )

    result = send_weather_reminders()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f"Weather Forecast for your trip: {trip.title}"
    assert "25" in mailoutbox[0].body
    assert "15" in mailoutbox[0].body
    assert mailoutbox[0].from_email == "Organize It <noreply@test.local>"

    # Check that weather_reminder_sent_at was updated
    trip.refresh_from_db()
    assert trip.weather_reminder_sent_at == today


def test_send_weather_reminders_uses_italian_for_italian_user(
    trip_factory, today, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    trip.author.profile.language = "it"
    trip.author.profile.save()
    Day.objects.create(
        trip=trip,
        number=1,
        date=target_date,
        weather_data={"temperature_max": 25, "temperature_min": 15},
    )

    send_weather_reminders()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject.startswith("Previsioni meteo")
    assert "si avvicina" in mailoutbox[0].body
    assert "25" in mailoutbox[0].body
    assert "15" in mailoutbox[0].body


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
        weather_data={"temperature_max": 25, "temperature_min": 15},
    )

    result = send_weather_reminders()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_weather_reminders_includes_collaborators(
    trip_factory, user_factory, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    collab1 = user_factory()
    collab2 = user_factory()
    _add_collaborator(trip, collab1, trip.author)
    _add_collaborator(trip, collab2, trip.author)
    _day_with_weather(trip, target_date)

    result = send_weather_reminders()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert msg.to == [trip.author.email]
    assert set(msg.bcc) == {collab1.email, collab2.email}


def test_send_weather_reminders_skips_collaborator_opted_out(
    trip_factory, user_factory, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    collab = user_factory()
    collab.profile.show_weather = False
    collab.profile.save()
    _add_collaborator(trip, collab, trip.author)
    _day_with_weather(trip, target_date)

    send_weather_reminders()

    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert msg.to == [trip.author.email]
    assert msg.bcc == []


def test_send_weather_reminders_skips_collaborator_unverified(
    trip_factory, user_factory, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    collab = user_factory()
    EmailAddress.objects.filter(user=collab).update(verified=False)
    _add_collaborator(trip, collab, trip.author)
    _day_with_weather(trip, target_date)

    send_weather_reminders()

    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert msg.to == [trip.author.email]
    assert msg.bcc == []


def test_send_weather_reminders_author_optout_collab_in(
    trip_factory, user_factory, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    trip.author.profile.show_weather = False
    trip.author.profile.save()
    collab = user_factory()
    _add_collaborator(trip, collab, trip.author)
    _day_with_weather(trip, target_date)

    result = send_weather_reminders()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert msg.to == [collab.email]
    assert msg.bcc == []


def test_send_weather_reminders_uses_author_language_for_all(
    trip_factory, user_factory, target_date, mailoutbox
):
    trip = trip_factory(start_date=target_date)
    trip.author.profile.language = "it"
    trip.author.profile.save()
    collab = user_factory()
    collab.profile.language = "en"
    collab.profile.save()
    _add_collaborator(trip, collab, trip.author)
    _day_with_weather(trip, target_date)

    send_weather_reminders()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject.startswith("Previsioni meteo")
