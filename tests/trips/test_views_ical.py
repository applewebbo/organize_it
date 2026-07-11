import datetime
import uuid

import pytest
from django.urls import reverse
from icalendar import Calendar

from trips.models import Day, MainTransfer

pytestmark = pytest.mark.django_db


def test_export_trip_ical_success(
    tp, trip, event_factory, stay_factory, main_transfer_factory
):
    # Setup trip and days
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 2)
    trip.save()

    day1 = Day.objects.create(trip=trip, number=1, date=datetime.date(2025, 1, 1))
    day2 = Day.objects.create(trip=trip, number=2, date=datetime.date(2025, 1, 2))

    # Create Event
    event_factory(
        trip=trip, day=day1, start_time=datetime.time(10, 0), name="Colosseum Tour"
    )

    # Create Stay
    stay = stay_factory(name="Hotel Roma")
    day1.stay = stay
    day1.save()
    day2.stay = stay
    day2.save()

    # Create MainTransfer
    main_transfer_factory(
        trip=trip,
        direction=MainTransfer.Direction.ARRIVAL,
        start_time=datetime.time(8, 0),
        end_time=datetime.time(9, 30),
        origin_name="JFK",
        destination_name="FCO",
    )

    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)

    tp.response_200(response)
    assert response["Content-Type"] == "text/calendar"

    # Parse ical
    cal = Calendar.from_ical(response.content)
    events = [component for component in cal.walk() if component.name == "VEVENT"]

    # We should have 3 events: 1 MainTransfer, 1 Stay, 1 Event
    assert len(events) == 3
    summaries = [str(ev.get("summary")) for ev in events]

    assert any("Colosseum Tour" in summary for summary in summaries)
    assert any("Hotel Roma" in summary for summary in summaries)
    assert any("JFK" in summary for summary in summaries)


def test_export_trip_ical_not_found(tp):
    url = reverse("trips:trip-ical", kwargs={"calendar_token": uuid.uuid4()})
    response = tp.get(url)
    tp.response_404(response)


def test_calendar_settings_modal_shows_feed_url(client, trip):
    client.force_login(trip.author)
    url = reverse("trips:trip-calendar-settings", kwargs={"trip_id": trip.pk})
    response = client.get(url)
    assert response.status_code == 200
    feed_path = reverse(
        "trips:trip-ical", kwargs={"calendar_token": trip.calendar_token}
    )
    assert feed_path in response.content.decode()


def test_calendar_settings_requires_owner(client, trip, user_factory):
    client.force_login(user_factory())
    url = reverse("trips:trip-calendar-settings", kwargs={"trip_id": trip.pk})
    response = client.get(url)
    assert response.status_code == 404


def test_rotate_calendar_token_changes_token(client, trip):
    client.force_login(trip.author)
    old_token = trip.calendar_token
    url = reverse("trips:trip-calendar-settings", kwargs={"trip_id": trip.pk})
    response = client.post(url)
    assert response.status_code == 200
    trip.refresh_from_db()
    assert trip.calendar_token != old_token


def test_rotate_calendar_token_invalidates_old_url(tp, client, trip):
    old_token = trip.calendar_token
    old_feed = reverse("trips:trip-ical", kwargs={"calendar_token": old_token})
    tp.response_200(tp.get(old_feed))

    client.force_login(trip.author)
    url = reverse("trips:trip-calendar-settings", kwargs={"trip_id": trip.pk})
    client.post(url)

    tp.response_404(tp.get(old_feed))
    trip.refresh_from_db()
    new_feed = reverse(
        "trips:trip-ical", kwargs={"calendar_token": trip.calendar_token}
    )
    tp.response_200(tp.get(new_feed))


def test_rotate_calendar_token_non_owner_forbidden(client, trip, user_factory):
    client.force_login(user_factory())
    old_token = trip.calendar_token
    url = reverse("trips:trip-calendar-settings", kwargs={"trip_id": trip.pk})
    response = client.post(url)
    assert response.status_code == 404
    trip.refresh_from_db()
    assert trip.calendar_token == old_token


def test_rotate_calendar_token_requires_login(client, trip):
    url = reverse("trips:trip-calendar-settings", kwargs={"trip_id": trip.pk})
    response = client.post(url)
    assert response.status_code == 302


def test_export_trip_ical_departure_transfer_with_notes(
    tp, trip, main_transfer_factory
):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 2)
    trip.save()
    main_transfer_factory(
        trip=trip,
        direction=MainTransfer.Direction.DEPARTURE,
        start_time=datetime.time(23, 30),
        end_time=datetime.time(1, 0),
        origin_name="FCO",
        destination_name="JFK",
        notes="bring snacks",
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 1
    assert "bring snacks" in str(events[0].get("description"))


def test_export_trip_ical_transfer_without_times_skipped(
    tp, trip, main_transfer_factory
):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 2)
    trip.save()
    main_transfer_factory(
        trip=trip,
        direction=MainTransfer.Direction.ARRIVAL,
        start_time=None,
        end_time=None,
        origin_name="JFK",
        destination_name="FCO",
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert events == []


def test_export_trip_ical_arrival_without_trip_dates_skipped(
    tp, trip, main_transfer_factory
):
    trip.start_date = None
    trip.end_date = None
    trip.save()
    main_transfer_factory(
        trip=trip,
        direction=MainTransfer.Direction.ARRIVAL,
        start_time=datetime.time(8, 0),
        end_time=datetime.time(10, 0),
        origin_name="JFK",
        destination_name="FCO",
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert events == []


def test_export_trip_ical_stay_with_address_and_notes(tp, trip, stay_factory):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 1)
    trip.save()
    day = Day.objects.create(trip=trip, number=1, date=datetime.date(2025, 1, 1))
    stay = stay_factory(name="Hotel Roma", address="Via Roma 1", notes="ground floor")
    day.stay = stay
    day.save()
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    stay_ev = next(c for c in cal.walk() if c.name == "VEVENT")
    assert "Via Roma 1" in str(stay_ev.get("location"))
    assert "ground floor" in str(stay_ev.get("description"))


def test_export_trip_ical_departure_same_day(tp, trip, main_transfer_factory):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 2)
    trip.save()
    main_transfer_factory(
        trip=trip,
        direction=MainTransfer.Direction.DEPARTURE,
        start_time=datetime.time(8, 0),
        end_time=datetime.time(10, 0),
        origin_name="FCO",
        destination_name="JFK",
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 1


def test_export_trip_ical_arrival_overnight(tp, trip, main_transfer_factory):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 2)
    trip.save()
    main_transfer_factory(
        trip=trip,
        direction=MainTransfer.Direction.ARRIVAL,
        start_time=datetime.time(23, 30),
        end_time=datetime.time(1, 0),
        origin_name="JFK",
        destination_name="FCO",
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 1


def test_export_trip_ical_stay_without_address_or_notes(tp, trip, stay_factory):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 1)
    trip.save()
    day = Day.objects.create(trip=trip, number=1, date=datetime.date(2025, 1, 1))
    stay = stay_factory(
        name="Bare Stay",
        address="",
        notes="",
        check_in=None,
        check_out=None,
        phone_number="",
        website="",
    )
    day.stay = stay
    day.save()
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    ev = next(c for c in cal.walk() if c.name == "VEVENT")
    assert ev.get("location") is None
    assert ev.get("description") is None


def test_export_trip_ical_event_without_address_or_notes(tp, trip, event_factory):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 1)
    trip.save()
    day = Day.objects.create(trip=trip, number=1, date=datetime.date(2025, 1, 1))
    event_factory(
        trip=trip,
        day=day,
        start_time=datetime.time(10, 0),
        name="Bare event",
        address="",
        notes="",
        website="",
        phone_number="",
        opening_hours=None,
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    ev = next(c for c in cal.walk() if c.name == "VEVENT")
    assert ev.get("location") is None
    assert ev.get("description") is None


def test_export_trip_ical_event_branches(tp, trip, event_factory):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 1)
    trip.save()
    day = Day.objects.create(trip=trip, number=1, date=datetime.date(2025, 1, 1))
    event_factory(
        trip=trip,
        day=day,
        start_time=datetime.time(10, 0),
        name="Tour with duration",
        estimated_duration=datetime.timedelta(hours=2),
        address="Via X 1",
        notes="bring water",
    )
    event_factory(
        trip=trip, day=day, start_time=None, name="Untimed", address="", notes=""
    )
    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 1
    ev = events[0]
    assert "Via X 1" in str(ev.get("location"))
    assert "bring water" in str(ev.get("description"))


def test_export_trip_ical_event_and_stay_with_phone_and_hours(
    tp, trip, event_factory, stay_factory
):
    trip.start_date = datetime.date(2025, 1, 1)
    trip.end_date = datetime.date(2025, 1, 1)
    trip.save()
    day = Day.objects.create(trip=trip, number=1, date=datetime.date(2025, 1, 1))

    opening_hours = {"0": "09:00 - 18:00"}  # Monday

    event_factory(
        trip=trip,
        day=day,
        start_time=datetime.time(10, 0),
        name="Test Event",
        phone_number="+123456789",
        website="https://example.com",
        opening_hours=opening_hours,
    )

    stay = stay_factory(
        name="Test Stay",
        phone_number="+987654321",
        website="https://stay.example.com",
        check_in=datetime.time(14, 0),
        check_out=datetime.time(10, 0),
    )
    day.stay = stay
    day.save()

    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 2

    # Both the activity event and the stay event carry phone/website/hours
    desc_concat = " ".join(str(e.get("description")) for e in events)
    assert "+123456789" in desc_concat
    assert "https://example.com" in desc_concat
    assert "Mon: 09:00 - 18:00" in desc_concat
    assert "https://stay.example.com" in desc_concat
