"""One-off maintenance command to fix wrong trip destination coordinates.

Re-geocodes every trip destination at place level (``types="place"``) so
coordinates that were previously stored from an ambiguous, country-level
match (e.g. "Roma" -> România) are corrected. Idempotent; supports
``--dry-run``.

Usage:
    uv run python manage.py regeocode_trip_destinations [--dry-run]
"""

import geocoder
from django.conf import settings
from django.core.management.base import BaseCommand

from trips.models import Trip


class Command(BaseCommand):
    help = "Re-geocode trip destinations at place level to fix wrong coordinates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        for trip in Trip.objects.exclude(destination=""):
            g = geocoder.mapbox(
                trip.destination,
                access_token=settings.MAPBOX_ACCESS_TOKEN,
                types="place",
            )
            if not g.latlng:
                continue
            lat, lng = g.latlng
            if (trip.destination_latitude, trip.destination_longitude) == (lat, lng):
                continue
            if not dry_run:
                # Bypass the pre_save signal (it would re-geocode) and write coords.
                Trip.objects.filter(pk=trip.pk).update(
                    destination_latitude=lat, destination_longitude=lng
                )
            updated += 1
            self.stdout.write(f"{trip.pk} {trip.destination}: {lat}, {lng}")

        prefix = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{prefix} {updated} trip(s)"))
