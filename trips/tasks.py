from datetime import date, timedelta

from django.conf import settings
from django.core import management

from trips.models import Trip


def populate_trips():
    if settings.DEBUG:
        management.call_command("populate_trips", "--settings=trips.settings.dev")
    else:
        management.call_command(
            "populate_trips", "--settings=trips.settings.production"
        )
    print("Trips populated correctly!")


def check_trips_status():
    trips = Trip.objects.all()
    trips_count = 0
    today = date.today()
    seven_days_after = today + timedelta(days=7)
    for trip in trips:
        trips_count += 1
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

        trip.save()
    print(f"{trips_count} trips status checked correctly!")
