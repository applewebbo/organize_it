"""
Django management command to geocode train stations without coordinates.
Usage: python manage.py geocode_stations [--limit N] [--dry-run]
"""

import csv
import time
from pathlib import Path

import geocoder
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Geocode train stations without coordinates using Mapbox API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of stations to geocode (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be geocoded without making changes",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.2,
            help="Delay between API calls in seconds (default: 0.2)",
        )

    def handle(self, *args, **options):
        csv_path = (
            Path(settings.BASE_DIR) / "trips" / "data" / "stations_simplified.csv"
        )
        limit = options["limit"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        # Read all stations
        stations = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stations.append(row)

        # Find stations without coordinates
        missing_coords = [
            s for s in stations if not s.get("latitude") or not s.get("longitude")
        ]

        self.stdout.write(
            self.style.WARNING(
                f"Found {len(missing_coords)} stations without coordinates"
            )
        )

        if limit:
            missing_coords = missing_coords[:limit]
            self.stdout.write(
                self.style.WARNING(f"Limited to {limit} stations for geocoding")
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            for station in missing_coords[:10]:  # Show first 10
                self.stdout.write(
                    f"  - {station['name']} ({station['country']}) - ID: {station['id']}"
                )
            if len(missing_coords) > 10:
                self.stdout.write(f"  ... and {len(missing_coords) - 10} more")
            return

        # Geocode missing stations
        geocoded_count = 0
        failed_count = 0

        for i, station in enumerate(missing_coords, 1):
            # Add "train station" to improve geocoding accuracy
            query = f"{station['name']} train station, {station['country']}"
            self.stdout.write(f"[{i}/{len(missing_coords)}] Geocoding: {query}")

            try:
                g = geocoder.mapbox(query, access_token=settings.MAPBOX_ACCESS_TOKEN)

                if g.latlng:
                    station["latitude"] = str(g.latlng[0])
                    station["longitude"] = str(g.latlng[1])
                    geocoded_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Found: {g.latlng[0]}, {g.latlng[1]}")
                    )
                else:
                    failed_count += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ No results for {query}"))

                # Rate limiting
                time.sleep(delay)

            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Error geocoding {query}: {e}"))

        # Write updated CSV
        if geocoded_count > 0:
            fieldnames = ["id", "name", "latitude", "longitude", "country"]
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(stations)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Successfully geocoded {geocoded_count} stations"
                )
            )

        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f"✗ Failed to geocode {failed_count} stations")
            )

        self.stdout.write(self.style.SUCCESS(f"\nCSV updated: {csv_path}"))
