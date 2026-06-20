import datetime

import pytest
from django.urls import reverse
from icalendar import Calendar

from trips.models import Day

pytestmark = pytest.mark.django_db


def test_export_trip_ical_event_with_phone_and_hours(tp, trip, event_factory):
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

    url = reverse("trips:trip-ical", kwargs={"calendar_token": trip.calendar_token})
    response = tp.get(url)
    tp.response_200(response)
    cal = Calendar.from_ical(response.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 1
    description = str(events[0].get("description"))

    assert "+123456789" in description
    assert "https://example.com" in description
    assert "Mon: 09:00 - 18:00" in description
