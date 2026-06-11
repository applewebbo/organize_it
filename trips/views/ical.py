import datetime

from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from icalendar import Calendar
from icalendar import Event as ICalEvent

from trips.models import MainTransfer, Trip


@login_not_required
def export_trip_ical(request, calendar_token):
    trip = get_object_or_404(Trip, calendar_token=calendar_token)

    cal = Calendar()
    cal.add("prodid", "-//Organize It//Webbo//IT")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", f"Trip: {trip.title}")

    # 1. Add Main Transfers
    for mt in trip.main_transfers.all():
        if mt.start_time and mt.end_time:
            if mt.direction == MainTransfer.Direction.ARRIVAL and trip.start_date:
                dt_start = datetime.datetime.combine(trip.start_date, mt.start_time)
                dt_end = datetime.datetime.combine(trip.start_date, mt.end_time)
                if dt_end < dt_start:
                    dt_end += datetime.timedelta(days=1)
            elif mt.direction == MainTransfer.Direction.DEPARTURE and trip.end_date:
                dt_start = datetime.datetime.combine(trip.end_date, mt.start_time)
                dt_end = datetime.datetime.combine(trip.end_date, mt.end_time)
                if dt_end < dt_start:
                    dt_end += datetime.timedelta(days=1)
            else:
                continue

            event = ICalEvent()
            event.add(
                "summary",
                f"{mt.get_type_display()}: {mt.origin_name} - {mt.destination_name}",
            )
            event.add("dtstart", dt_start)
            event.add("dtend", dt_end)
            event.add("location", f"{mt.origin_name} to {mt.destination_name}")
            if mt.notes:
                event.add("description", mt.notes)
            cal.add_component(event)

    # 2. Add Stays
    stays_dict = {}
    for day in trip.days.filter(stay__isnull=False).select_related("stay"):
        stay = day.stay
        if stay.id not in stays_dict:
            stays_dict[stay.id] = {"stay": stay, "days": []}
        stays_dict[stay.id]["days"].append(day.date)

    for stay_data in stays_dict.values():
        stay = stay_data["stay"]
        dates = sorted(stay_data["days"])
        start_date = dates[0]
        end_date = dates[-1] + datetime.timedelta(days=1)

        event = ICalEvent()
        event.add("summary", f"Soggiorno: {stay.name}")
        event.add("dtstart", start_date)
        event.add("dtend", end_date)
        if stay.address:
            event.add("location", stay.address)
        if stay.notes:
            event.add("description", stay.notes)
        cal.add_component(event)

    # 3. Add Events
    for day in trip.days.prefetch_related("events"):
        for ev in day.events.all():
            if ev.start_time:
                dt_start = datetime.datetime.combine(day.date, ev.start_time)
                if ev.estimated_duration:
                    dt_end = dt_start + ev.estimated_duration
                else:
                    dt_end = dt_start + datetime.timedelta(hours=1)

                event = ICalEvent()
                event.add("summary", ev.name)
                event.add("dtstart", dt_start)
                event.add("dtend", dt_end)
                if ev.address:
                    event.add("location", ev.address)
                if ev.notes:
                    event.add("description", ev.notes)
                cal.add_component(event)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = (
        f'attachment; filename="{trip.title}_calendar.ics"'
    )
    return response
