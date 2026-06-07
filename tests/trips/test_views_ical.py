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
