"""Background tasks for trips app using django-q2."""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import management
from django.utils import timezone

from trips.models import Trip

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
        expired_count = Session.objects.filter(expire_date__lt=timezone.now()).count()

        if expired_count > 0:
            Session.objects.filter(expire_date__lt=timezone.now()).delete()
            result_msg = f"Deleted {expired_count} expired sessions"
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
