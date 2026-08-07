"""Background tasks for trips app using django-q2."""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import management
from django.utils import timezone

from trips.models import Day, MainTransfer, Trip
from trips.utils import fetch_route
from trips.weather import fetch_weather_for_trip

logger = logging.getLogger("task")


def _attach_unsplash_photo(trip, photo_data, extra_metadata=None):
    """Download an Unsplash photo and store it as the trip cover.

    Returns True when the photo was attached, False on any failure.
    """
    from trips.utils import download_unsplash_photo, process_trip_image

    image_content, metadata = download_unsplash_photo(photo_data)
    if not image_content:
        return False

    processed_image = process_trip_image(image_content)
    if not processed_image:
        return False

    photo_id = photo_data.get("id", "unknown")
    filename = f"trip_{trip.pk}_{photo_id}.jpg"
    trip.image.save(filename, processed_image, save=False)
    trip.image_metadata = {**metadata, **(extra_metadata or {})}
    trip.save(update_fields=["image", "image_metadata"])
    logger.info("Unsplash photo %s attached to trip %s", photo_id, trip.pk)
    return True


def download_trip_unsplash_photo(trip_pk, photo_data):
    """Download and attach an Unsplash photo to a trip."""
    try:
        trip = Trip.objects.get(pk=trip_pk)
    except Trip.DoesNotExist:
        logger.warning("download_trip_unsplash_photo: trip %s not found", trip_pk)
        return

    _attach_unsplash_photo(trip, photo_data)


def auto_select_trip_cover(trip_pk):
    """Pick an Unsplash cover for a trip from its destination, no user choice.

    Used by the creation wizard (issue #422): the first matching photo wins and
    the metadata is flagged as auto-selected so the UI can badge it. Any failure
    clears the pending flag so the placeholder is shown instead of a spinner.
    """
    from trips.utils import search_unsplash_photos

    try:
        trip = Trip.objects.get(pk=trip_pk)
    except Trip.DoesNotExist:
        logger.warning("auto_select_trip_cover: trip %s not found", trip_pk)
        return

    # Never overwrite an image the user provided during the wizard.
    if trip.image:
        return

    photos = search_unsplash_photos(trip.destination, per_page=1)
    if not photos or not _attach_unsplash_photo(
        trip, photos[0], {"auto_selected": True}
    ):
        logger.info("auto_select_trip_cover: no cover found for trip %s", trip_pk)
        trip.image_metadata = {}
        trip.save(update_fields=["image_metadata"])


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
    """Return (lat, lng) for a day. Priority: destination coords → stay → first geocoded event → trip destination."""
    if day.destination_latitude is not None and day.destination_longitude is not None:
        return day.destination_latitude, day.destination_longitude
    if day.stay and day.stay.latitude is not None and day.stay.longitude is not None:
        return day.stay.latitude, day.stay.longitude
    event = day.events.filter(latitude__isnull=False, longitude__isnull=False).first()
    if event:
        return event.latitude, event.longitude
    if (
        day.destination == day.trip.destination
        and day.trip.destination_latitude is not None
        and day.trip.destination_longitude is not None
    ):
        return day.trip.destination_latitude, day.trip.destination_longitude
    return None, None


def _get_home_coords(trip):
    """Return (lat, lng) from trip author's profile home address, or (None, None)."""
    profile = getattr(trip.author, "profile", None)
    if profile and profile.home_address_latitude and profile.home_address_longitude:
        return profile.home_address_latitude, profile.home_address_longitude
    return None, None


def calculate_day_transfer(day_pk):
    """
    Calculate driving duration/distance for the transfer arriving at day_pk and,
    if it is the last day of the trip, the return transfer to the author's home.

    For day 1 with no ARRIVAL MainTransfer: uses profile home address as origin.
    For last day with no DEPARTURE MainTransfer: calculates from day to home address.
    Clears fields when conditions are not met or coords are unavailable.
    """
    try:
        day = (
            Day.objects.select_related("trip__author__profile", "stay")
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
    is_last_day = not Day.objects.filter(trip=day.trip, number=day.number + 1).exists()

    # --- from_prev calculation ---
    if prev_day is None:
        # Day 1: use home address as origin if no ARRIVAL MainTransfer
        has_arrival = MainTransfer.objects.filter(
            trip=day.trip, direction=MainTransfer.Direction.ARRIVAL
        ).exists()
        if has_arrival:
            Day.objects.filter(pk=day_pk).update(
                transfer_duration_from_prev=None, transfer_distance_from_prev=None
            )
        else:
            lat1, lng1 = _get_home_coords(day.trip)
            lat2, lng2 = _get_day_coords(day)
            if lat1 is not None and lat2 is not None:
                result = fetch_route(lat1, lng1, lat2, lng2)
                if result:
                    Day.objects.filter(pk=day_pk).update(
                        transfer_duration_from_prev=result[0],
                        transfer_distance_from_prev=result[1],
                    )
                    logger.debug(f"Home→day {day_pk}: {result[0]}min, {result[1]}km")
                else:
                    Day.objects.filter(pk=day_pk).update(
                        transfer_duration_from_prev=None,
                        transfer_distance_from_prev=None,
                    )
            else:
                Day.objects.filter(pk=day_pk).update(
                    transfer_duration_from_prev=None, transfer_distance_from_prev=None
                )
    elif prev_day.destination == day.destination:
        Day.objects.filter(pk=day_pk).update(
            transfer_duration_from_prev=None, transfer_distance_from_prev=None
        )
    else:
        lat1, lng1 = _get_day_coords(prev_day)
        lat2, lng2 = _get_day_coords(day)
        if lat1 is None or lat2 is None:
            Day.objects.filter(pk=day_pk).update(
                transfer_duration_from_prev=None, transfer_distance_from_prev=None
            )
        else:
            result = fetch_route(lat1, lng1, lat2, lng2)
            if result:
                Day.objects.filter(pk=day_pk).update(
                    transfer_duration_from_prev=result[0],
                    transfer_distance_from_prev=result[1],
                )
                logger.debug(f"Transfer to day {day_pk}: {result[0]}min, {result[1]}km")
            else:
                Day.objects.filter(pk=day_pk).update(
                    transfer_duration_from_prev=None, transfer_distance_from_prev=None
                )

    # --- to_home calculation (last day only) ---
    if not is_last_day:
        Day.objects.filter(pk=day_pk).update(
            transfer_to_home_duration=None, transfer_to_home_distance=None
        )
        return

    has_departure = MainTransfer.objects.filter(
        trip=day.trip, direction=MainTransfer.Direction.DEPARTURE
    ).exists()
    if has_departure:
        Day.objects.filter(pk=day_pk).update(
            transfer_to_home_duration=None, transfer_to_home_distance=None
        )
        return

    lat1, lng1 = _get_day_coords(day)
    lat2, lng2 = _get_home_coords(day.trip)
    if lat1 is None or lat2 is None:
        Day.objects.filter(pk=day_pk).update(
            transfer_to_home_duration=None, transfer_to_home_distance=None
        )
        return

    result = fetch_route(lat1, lng1, lat2, lng2)
    if result:
        Day.objects.filter(pk=day_pk).update(
            transfer_to_home_duration=result[0], transfer_to_home_distance=result[1]
        )
        logger.debug(f"Day {day_pk}→home: {result[0]}min, {result[1]}km")
    else:
        Day.objects.filter(pk=day_pk).update(
            transfer_to_home_duration=None, transfer_to_home_distance=None
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
        trips = list(
            Trip.objects.exclude(status=5).filter(
                start_date__isnull=False, end_date__isnull=False
            )
        )
        trips_count = len(trips)
        today = date.today()
        seven_days_after = today + timedelta(days=7)
        to_update = []

        for trip in trips:
            original_status = trip.status

            if trip.end_date < today:
                trip.status = 4
            elif trip.start_date <= today <= trip.end_date:
                trip.status = 3
            elif today < trip.start_date < seven_days_after:
                trip.status = 2
            elif trip.start_date >= seven_days_after:
                trip.status = 1

            if trip.status != original_status:
                to_update.append(trip)
                logger.debug(
                    f"Trip '{trip.title}' status changed from {original_status} to {trip.status}"
                )

        Trip.objects.bulk_update(to_update, ["status"])
        modified_trips_count = len(to_update)

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


def cleanup_abandoned_wizard_trips():
    """
    Delete creation-wizard drafts abandoned for more than 24 hours.

    A draft is a Trip with ``wizard_completed=False``; ``wizard_started_at``
    timestamps when the wizard began. Instances are deleted one by one so the
    Trip.delete() override (which clears linked expenses) runs.

    Returns:
        int: Number of abandoned draft trips deleted
    """
    cutoff = timezone.now() - timedelta(hours=24)
    stale = Trip.objects.filter(wizard_completed=False, wizard_started_at__lt=cutoff)
    deleted = 0
    for trip in stale:
        trip.delete()
        deleted += 1
    if deleted:
        logger.info(f"Deleted {deleted} abandoned wizard draft trips")
    return deleted


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


def _build_checklist_url(trip):
    """Build absolute URL for the trip checklist page."""
    from django.urls import reverse

    hosts = [h for h in settings.ALLOWED_HOSTS if h not in ("*",)]
    domain = hosts[0] if hosts else "localhost:8000"
    scheme = "https" if settings.ENVIRONMENT == "prod" else "http"
    path = reverse("trips:trip-checklist", kwargs={"pk": trip.pk})
    return f"{scheme}://{domain}{path}"


def _send_checklist_reminder_email(trip, pending, today):
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.translation import override as translation_override

    recipient_language = getattr(trip.author.profile, "language", "en")
    context = {
        "trip": trip,
        "pending_items": pending,
        "days_to_departure": (trip.start_date - today).days,
        "trip_url": _build_checklist_url(trip),
    }
    with translation_override(recipient_language):
        subject = render_to_string(
            "trips/email/checklist_reminder_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/checklist_reminder_body.txt", context)
        html_body = render_to_string(
            "trips/email/checklist_reminder_body.html", context
        )
    msg = EmailMultiAlternatives(
        subject=subject, body=text_body, to=[trip.author.email]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
    Trip.objects.filter(pk=trip.pk).update(checklist_reminder_sent_at=today)
    logger.info(
        f"Checklist reminder sent for trip '{trip.title}' to {trip.author.email}"
    )


def send_checklist_reminders():
    """Send checklist reminder emails for trips whose reminder day matches today."""
    try:
        logger.info("Starting send_checklist_reminders task")
        today = timezone.now().date()
        trips = (
            Trip.objects.filter(
                checklist_reminder_days__isnull=False,
                start_date__isnull=False,
            )
            .exclude(checklist_reminder_sent_at=today)
            .select_related("author__profile")
        )
        sent = 0
        for trip in trips:
            trigger_date = trip.start_date - timedelta(
                days=trip.checklist_reminder_days
            )
            if trigger_date == today:
                pending = trip.checklist_items.filter(completed=False)
                if pending.exists():
                    _send_checklist_reminder_email(trip, list(pending), today)
                    sent += 1
        result_msg = f"Checklist reminders sent: {sent}"
        logger.info(f"send_checklist_reminders completed: {result_msg}")
        return result_msg
    except Exception as e:
        logger.error(f"Error in send_checklist_reminders task: {e}", exc_info=True)
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
            status__in=[Trip.Status.IMPENDING, Trip.Status.IN_PROGRESS],
            author__profile__show_weather=True,
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


def _build_trip_url(trip):
    """Build absolute URL for the trip detail page."""
    from django.urls import reverse

    hosts = [h for h in settings.ALLOWED_HOSTS if h not in ("*",)]
    domain = hosts[0] if hosts else "localhost:8000"
    scheme = "https" if settings.ENVIRONMENT == "prod" else "http"
    path = reverse("trips:trip-detail", kwargs={"pk": trip.pk})
    return f"{scheme}://{domain}{path}"


def _eligible_weather_recipients(trip):
    """Return email addresses eligible to receive the weather reminder.

    Includes the trip author plus accepted (registered) collaborators, filtered by:
    - profile.show_weather is True
    - the user has a verified email address (allauth)
    Author is always first if eligible, to keep them in the visible `to` field.
    """
    from allauth.account.models import EmailAddress

    candidates = [trip.author]
    candidates.extend(
        c.user for c in trip.collaborations.select_related("user__profile") if c.user
    )
    verified_user_ids = set(
        EmailAddress.objects.filter(
            user__in=[u.pk for u in candidates],
            verified=True,
        ).values_list("user_id", flat=True)
    )
    recipients = []
    for user in candidates:
        if not getattr(getattr(user, "profile", None), "show_weather", True):
            continue
        if user.pk not in verified_user_ids:
            continue
        if user.email and user.email not in recipients:
            recipients.append(user.email)
    return recipients


def _send_weather_reminder_email(trip, today):
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.translation import override as translation_override

    recipients = _eligible_weather_recipients(trip)
    if not recipients:
        return False
    days_with_weather = trip.days.filter(weather_data__isnull=False).order_by("number")[
        :3
    ]
    if not days_with_weather.exists():
        return False

    recipient_language = getattr(trip.author.profile, "language", "en")
    context = {
        "trip": trip,
        "days": days_with_weather,
        "trip_url": _build_trip_url(trip),
    }
    with translation_override(recipient_language):
        subject = render_to_string(
            "trips/email/weather_reminder_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/weather_reminder_body.txt", context)
        html_body = render_to_string("trips/email/weather_reminder_body.html", context)
    msg = EmailMultiAlternatives(
        subject=subject, body=text_body, to=[recipients[0]], bcc=recipients[1:]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
    Trip.objects.filter(pk=trip.pk).update(weather_reminder_sent_at=today)
    logger.info(
        f"Weather reminder sent for trip '{trip.title}' to {len(recipients)} recipient(s)"
    )
    return True


def _eligible_digest_recipients(trip):
    """Return email addresses eligible to receive the daily digest.

    Author + accepted collaborators, filtered by:
    - profile.notify_daily_digest is True
    - the user has a verified email (allauth)
    Author is first if eligible, to keep them in the visible ``to`` field.
    """
    from allauth.account.models import EmailAddress

    candidates = [trip.author]
    candidates.extend(
        c.user for c in trip.collaborations.select_related("user__profile") if c.user
    )
    verified_user_ids = set(
        EmailAddress.objects.filter(
            user__in=[u.pk for u in candidates], verified=True
        ).values_list("user_id", flat=True)
    )
    recipients = []
    for user in candidates:
        if not getattr(getattr(user, "profile", None), "notify_daily_digest", True):
            continue
        if user.pk not in verified_user_ids:
            continue
        if user.email and user.email not in recipients:
            recipients.append(user.email)
    return recipients


def _get_digest_day_context(trip, today):
    """Collect everything relevant for the digest of ``today`` in ``trip``.

    Returns a dict with day, events, stay info and main transfers, or None
    if today's date is outside the trip date range.
    """
    day = (
        trip.days.prefetch_related("events", "stay")
        .filter(date=today)
        .select_related("stay")
        .first()
    )
    if day is None:
        return None

    events = list(day.events.all().order_by("start_time", "order", "pk"))

    stay = day.stay
    check_in = False
    check_out = False
    stay_start_date = None
    stay_end_date = None
    if stay is not None:
        stay_days = list(stay.days.order_by("number").values_list("date", flat=True))
        if stay_days:
            check_in = stay_days[0] == today
            check_out = stay_days[-1] == today
            stay_start_date = stay_days[0]
            stay_end_date = stay_days[-1]

    arrival = trip.main_transfers.filter(
        direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure = trip.main_transfers.filter(
        direction=MainTransfer.Direction.DEPARTURE
    ).first()
    main_transfers = []
    if arrival and trip.start_date == today:
        main_transfers.append(arrival)
    if departure and trip.end_date == today:
        main_transfers.append(departure)

    total_days = trip.days.count()
    return {
        "day": day,
        "events": events,
        "stay": stay,
        "check_in": check_in,
        "check_out": check_out,
        "stay_start_date": stay_start_date,
        "stay_end_date": stay_end_date,
        "main_transfers": main_transfers,
        "total_days": total_days,
    }


def _send_daily_digest_email(trip, today):
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.translation import override as translation_override

    recipients = _eligible_digest_recipients(trip)
    if not recipients:
        return False

    day_context = _get_digest_day_context(trip, today)
    if day_context is None:
        return False

    recipient_language = getattr(trip.author.profile, "language", "en")
    context = {
        "trip": trip,
        "today": today,
        "trip_url": _build_trip_url(trip),
        **day_context,
    }
    with translation_override(recipient_language):
        subject = render_to_string(
            "trips/email/daily_digest_subject.txt", context
        ).strip()
        text_body = render_to_string("trips/email/daily_digest_body.txt", context)
        html_body = render_to_string("trips/email/daily_digest_body.html", context)
    msg = EmailMultiAlternatives(
        subject=subject, body=text_body, to=[recipients[0]], bcc=recipients[1:]
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
    Trip.objects.filter(pk=trip.pk).update(daily_digest_sent_on=today)
    logger.info(
        f"Daily digest sent for trip '{trip.title}' to {len(recipients)} recipient(s)"
    )
    return True


def send_daily_digests():
    """Send the daily 'today on your trip' digest for active trips."""
    try:
        logger.info("Starting send_daily_digests task")
        today = timezone.now().date()
        trips = (
            Trip.objects.filter(
                status__in=[Trip.Status.IMPENDING, Trip.Status.IN_PROGRESS],
                start_date__lte=today,
                end_date__gte=today,
            )
            .exclude(daily_digest_sent_on=today)
            .select_related("author__profile")
            .prefetch_related("days", "collaborations__user__profile", "main_transfers")
        )
        sent = 0
        for trip in trips:
            if _send_daily_digest_email(trip, today):
                sent += 1
        result_msg = f"Daily digests sent: {sent}"
        logger.info(f"send_daily_digests completed: {result_msg}")
        return result_msg
    except Exception as e:
        logger.error(f"Error in send_daily_digests task: {e}", exc_info=True)
        raise


def send_weather_reminders():
    """Send weather reminder emails 3 days before departure."""
    try:
        logger.info("Starting send_weather_reminders task")
        today = timezone.now().date()
        target_start_date = today + timedelta(days=3)

        trips = (
            Trip.objects.prefetch_related("days", "collaborations__user__profile")
            .filter(start_date=target_start_date)
            .exclude(weather_reminder_sent_at=today)
            .select_related("author__profile")
        )
        sent = 0
        for trip in trips:
            if _send_weather_reminder_email(trip, today):
                sent += 1

        result_msg = f"Weather reminders sent: {sent}"
        logger.info(f"send_weather_reminders completed: {result_msg}")
        return result_msg
    except Exception as e:
        logger.error(f"Error in send_weather_reminders task: {e}", exc_info=True)
        raise
