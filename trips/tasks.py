"""Background tasks for trips app using django-q2."""

import logging
from datetime import date, timedelta

import requests
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import management
from django.utils import timezone

from trips.models import Day, Trip
from trips.weather import fetch_weather_for_trip

logger = logging.getLogger("task")


def populate_trips():
    """
    Populate database with dummy trips for development.

    Returns:
        str: Success message
    """
    try:
        logger.info("Starting populate_trips task")
        if settings.DEBUG:
            management.call_command("populate_trips", "--settings=trips.settings.dev")
        else:
            management.call_command(
                "populate_trips", "--settings=trips.settings.production"
            )
        logger.info("Task populate_trips completed successfully")
        return "Trips populated successfully"
    except Exception as e:
        logger.error(f"Error in populate_trips task: {e}", exc_info=True)
        raise


def _get_day_coords(day):
    """Return (lat, lng) for a day. Priority: destination coords → stay → first geocoded event."""
    if day.destination_latitude is not None and day.destination_longitude is not None:
        return day.destination_latitude, day.destination_longitude
    if day.stay and day.stay.latitude is not None and day.stay.longitude is not None:
        return day.stay.latitude, day.stay.longitude
    event = day.events.filter(latitude__isnull=False, longitude__isnull=False).first()
    if event:
        return event.latitude, event.longitude
    return None, None


def calculate_day_transfer(day_pk):
    """
    Calculate driving duration and distance for the transfer arriving at day_pk.
    day_pk must be the first day of a stage. Looks at day.number - 1 as the origin.
    Saves results on Day.transfer_duration_from_prev (minutes) and
    Day.transfer_distance_from_prev (km). Clears fields if same destination or no coords.
    """
    try:
        day = (
            Day.objects.select_related("trip", "stay")
            .prefetch_related("events")
            .get(pk=day_pk)
        )
    except Day.DoesNotExist:
        return

    prev_day = (
        Day.objects.select_related("stay")
        .prefetch_related("events")
        .filter(trip=day.trip, number=day.number - 1)
        .first()
    )

    has_different_dest = prev_day and prev_day.destination != day.destination
    if not has_different_dest:
        Day.objects.filter(pk=day_pk).update(
            transfer_duration_from_prev=None,
            transfer_distance_from_prev=None,
        )
        return

    lat1, lng1 = _get_day_coords(prev_day)
    lat2, lng2 = _get_day_coords(day)

    if lat1 is None or lat2 is None:
        Day.objects.filter(pk=day_pk).update(
            transfer_duration_from_prev=None,
            transfer_distance_from_prev=None,
        )
        return

    url = (
        f"https://api.mapbox.com/directions/v5/mapbox/driving/"
        f"{lng1},{lat1};"
        f"{lng2},{lat2}"
    )
    try:
        resp = requests.get(
            url, params={"access_token": settings.MAPBOX_ACCESS_TOKEN}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Mapbox Directions API error for day {day_pk}: {e}")
        return

    if data.get("routes"):
        route = data["routes"][0]
        Day.objects.filter(pk=day_pk).update(
            transfer_duration_from_prev=round(route["duration"] / 60),
            transfer_distance_from_prev=round(route["distance"] / 1000),
        )
        logger.debug(
            f"Transfer calculated for day {day_pk}: "
            f"{route['duration'] / 60:.0f}min, {route['distance'] / 1000:.0f}km"
        )


def check_trips_status():
    """
    Check and update trip status based on dates.

    Updates trip status to:
    - NOT_STARTED (1): More than 7 days before start
    - IMPENDING (2): Less than 7 days before start
    - IN_PROGRESS (3): Between start and end date
    - COMPLETED (4): After end date
    - ARCHIVED (5): Manually archived (no auto-update)

    Returns:
        str: Summary of checked and modified trips
    """
    try:
        logger.info("Starting check_trips_status task")
        trips = Trip.objects.all()
        trips_count = 0
        modified_trips_count = 0
        today = date.today()
        seven_days_after = today + timedelta(days=7)

        for trip in trips:
            trips_count += 1
            original_status = trip.status

            # Skip archived trips (status 5)
            if trip.status == 5:
                continue

            if trip.start_date and trip.end_date:
                # After end date
                if trip.end_date < today:
                    trip.status = 4
                # Between start date and end date
                elif trip.start_date <= today <= trip.end_date:
                    trip.status = 3
                # Less than 7 days from start date
                elif today < trip.start_date < seven_days_after:
                    trip.status = 2
                # More than 7 days from start date
                elif trip.start_date >= seven_days_after:
                    trip.status = 1

                if trip.status != original_status:
                    modified_trips_count += 1
                    trip.save(update_fields=["status"])
                    logger.debug(
                        f"Trip '{trip.title}' status changed from {original_status} to {trip.status}"
                    )

        result_msg = (
            f"{trips_count} trips checked, {modified_trips_count} trips modified"
        )
        logger.info(f"check_trips_status completed: {result_msg}")
        return result_msg

    except Exception as e:
        logger.error(f"Error in check_trips_status task: {e}", exc_info=True)
        raise


def cleanup_old_sessions():
    """
    Delete expired sessions from database.

    Returns:
        str: Summary of deleted sessions
    """
    try:
        logger.info("Starting cleanup_old_sessions task")
        deleted_count, _ = Session.objects.filter(
            expire_date__lt=timezone.now()
        ).delete()

        if deleted_count > 0:
            result_msg = f"Deleted {deleted_count} expired sessions"
            logger.info(result_msg)
            return result_msg
        else:
            logger.info("No expired sessions to delete")
            return "No expired sessions found"

    except Exception as e:
        logger.error(f"Error in cleanup_old_sessions task: {e}", exc_info=True)
        raise


def backup_database():
    """
    Backup database using django-dbbackup.

    Returns:
        str: Success message
    """
    try:
        logger.info("Starting database backup task")
        management.call_command("dbbackup", "--clean")
        result_msg = "Database backup completed successfully"
        logger.info(result_msg)
        return result_msg

    except Exception as e:
        logger.error(f"Error in backup_database task: {e}", exc_info=True)
        raise


def fetch_weather_for_active_trips():
    """
    Fetch and cache weather forecasts for all IMPENDING and IN_PROGRESS trips.

    Runs every 6 hours via django-q2 schedule.

    Returns:
        str: Summary of trips processed
    """
    try:
        logger.info("Starting fetch_weather_for_active_trips task")
        trips = Trip.objects.prefetch_related("days__events", "days__stay").filter(
            status__in=[Trip.Status.IMPENDING, Trip.Status.IN_PROGRESS]
        )
        count = trips.count()
        for trip in trips:
            fetch_weather_for_trip(trip)
            logger.debug(f"Weather fetched for trip '{trip.title}'")
        result_msg = f"Weather fetched for {count} trip(s)"
        logger.info(f"fetch_weather_for_active_trips completed: {result_msg}")
        return result_msg
    except Exception as e:
        logger.error(
            f"Error in fetch_weather_for_active_trips task: {e}", exc_info=True
        )
        raise
