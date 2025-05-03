import logging
from datetime import date, timedelta

from django.conf import settings
from django.core import management

from trips.models import Trip

logger = logging.getLogger("task")


def populate_trips():
    if settings.DEBUG:
        management.call_command("populate_trips", "--settings=trips.settings.dev")
    else:
        management.call_command(
            "populate_trips", "--settings=trips.settings.production"
        )
    logger.info("Task populate_trips run correctly!")
    print("Trips populated correctly!")


def check_trips_status():
    trips = Trip.objects.all()
    trips_count = 0
    modified_trips_count = 0
    today = date.today()
    seven_days_after = today + timedelta(days=7)
    for trip in trips:
        trips_count += 1
        original_status = trip.status
        if trip.start_date and trip.end_date:
            # add the case for when status is 5 to bypass date checks
            if trip.status == 5:
                return
            # after end date
            if trip.end_date < today:
                trip.status = 4
            # between start date and end date
            elif trip.start_date <= today and trip.end_date >= today:
                trip.status = 3
            # less than 7 days from start date
            elif trip.start_date < seven_days_after and trip.start_date > today:
                trip.status = 2
            # more than 7 days from start date
            elif trip.start_date <= seven_days_after:
                trip.status = 1

        if trip.status != original_status:
            modified_trips_count += 1
            trip.save()
    logger.info(f"{trips_count} trips checked, {modified_trips_count} trips modified.")
    print(f"{trips_count} trips checked, {modified_trips_count} trips modified.")
