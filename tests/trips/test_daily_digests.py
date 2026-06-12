import datetime

import pytest
from allauth.account.models import EmailAddress
from django.utils import timezone

from trips.models import MainTransfer, Trip, TripCollaboration
from trips.tasks import send_daily_digests

pytestmark = pytest.mark.django_db


def _add_collaborator(trip, user, owner):
    return TripCollaboration.objects.create(
        trip=trip, user=user, color="blue", added_by=owner
    )


@pytest.fixture
def today():
    return timezone.now().date()


@pytest.fixture
def active_trip(trip_factory, today):
    trip = trip_factory(
        start_date=today,
        end_date=today + datetime.timedelta(days=2),
    )
    return trip


def test_send_daily_digests_sends_email(active_trip, today, mailoutbox):
    active_trip.author.profile.language = "en"
    active_trip.author.profile.save()
    day = active_trip.days.get(date=today)
    day.weather_data = {"temperature_max": 25, "temperature_min": 15}
    day.save()

    result = send_daily_digests()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert active_trip.title in msg.subject
    assert "Day 1 of 3" in msg.subject
    assert "25" in msg.body
    assert "15" in msg.body
    assert msg.to == [active_trip.author.email]

    active_trip.refresh_from_db()
    assert active_trip.daily_digest_sent_on == today


def test_send_daily_digests_idempotent(active_trip, today, mailoutbox):
    active_trip.daily_digest_sent_on = today
    active_trip.save()

    result = send_daily_digests()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_daily_digests_skips_finished_trip(trip_factory, today, mailoutbox):
    trip_factory(
        start_date=today - datetime.timedelta(days=5),
        end_date=today - datetime.timedelta(days=2),
    )

    result = send_daily_digests()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_daily_digests_skips_future_trip(trip_factory, today, mailoutbox):
    trip_factory(
        start_date=today + datetime.timedelta(days=2),
        end_date=today + datetime.timedelta(days=5),
    )

    result = send_daily_digests()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_daily_digests_first_day_impending(trip_factory, today, mailoutbox):
    trip = trip_factory(start_date=today, end_date=today + datetime.timedelta(days=3))
    Trip.objects.filter(pk=trip.pk).update(status=Trip.Status.IMPENDING)

    result = send_daily_digests()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1


def test_send_daily_digests_italian_language(active_trip, today, mailoutbox):
    active_trip.author.profile.language = "it"
    active_trip.author.profile.save()

    send_daily_digests()

    assert len(mailoutbox) == 1
    assert "Giorno 1 di 3" in mailoutbox[0].subject


def test_send_daily_digests_no_content_sends_anyway(active_trip, today, mailoutbox):
    """Per user decision: send even when day has no events/weather/stay."""
    result = send_daily_digests()

    assert "sent: 1" in result
    assert len(mailoutbox) == 1
    assert "No events" in mailoutbox[0].body or "Nessun" in mailoutbox[0].body


def test_send_daily_digests_includes_collaborators(
    active_trip, user_factory, mailoutbox
):
    collab1 = user_factory()
    collab2 = user_factory()
    _add_collaborator(active_trip, collab1, active_trip.author)
    _add_collaborator(active_trip, collab2, active_trip.author)

    send_daily_digests()

    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert msg.to == [active_trip.author.email]
    assert set(msg.bcc) == {collab1.email, collab2.email}


def test_send_daily_digests_skips_collaborator_opt_out(
    active_trip, user_factory, mailoutbox
):
    collab = user_factory()
    collab.profile.notify_daily_digest = False
    collab.profile.save()
    _add_collaborator(active_trip, collab, active_trip.author)

    send_daily_digests()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].bcc == []


def test_send_daily_digests_skips_collaborator_unverified(
    active_trip, user_factory, mailoutbox
):
    collab = user_factory()
    EmailAddress.objects.filter(user=collab).update(verified=False)
    _add_collaborator(active_trip, collab, active_trip.author)

    send_daily_digests()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].bcc == []


def test_send_daily_digests_author_opt_out(active_trip, mailoutbox):
    active_trip.author.profile.notify_daily_digest = False
    active_trip.author.profile.save()

    result = send_daily_digests()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0


def test_send_daily_digests_includes_events(
    active_trip, today, experience_factory, mailoutbox
):
    day = active_trip.days.get(date=today)
    experience_factory(
        trip=active_trip,
        day=day,
        name="Visit Colosseum",
        start_time=datetime.time(10, 30),
        latitude=41.89,
        longitude=12.49,
    )

    send_daily_digests()

    assert len(mailoutbox) == 1
    assert "Visit Colosseum" in mailoutbox[0].body
    assert "10:30" in mailoutbox[0].body


def test_send_daily_digests_stay_check_in_out(
    active_trip, today, stay_factory, mailoutbox
):
    day = active_trip.days.get(date=today)
    stay = stay_factory(
        name="Hotel Roma",
        address="Via Test 1",
        latitude=41.9,
        longitude=12.5,
    )
    day.stay = stay
    day.save()

    send_daily_digests()

    assert len(mailoutbox) == 1
    body = mailoutbox[0].body
    assert "Hotel Roma" in body
    assert "Check-in" in body
    assert "Check-out" in body


def test_send_daily_digests_main_transfer_arrival(
    active_trip, today, main_transfer_factory, mailoutbox
):
    main_transfer_factory(
        trip=active_trip,
        direction=MainTransfer.Direction.ARRIVAL,
        origin_name="FCO",
        destination_name="Rome Termini",
        start_time=datetime.time(8, 0),
    )

    send_daily_digests()

    assert len(mailoutbox) == 1
    assert "FCO" in mailoutbox[0].body
    assert "Rome Termini" in mailoutbox[0].body


def test_send_daily_digests_excludes_archived(trip_factory, today, mailoutbox):
    trip_factory(
        start_date=today,
        end_date=today + datetime.timedelta(days=2),
        status=Trip.Status.ARCHIVED,
    )

    result = send_daily_digests()

    assert "sent: 0" in result
    assert len(mailoutbox) == 0
