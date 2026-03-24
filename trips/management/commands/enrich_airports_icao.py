"""
One-shot management command to enrich airports_simple.csv with ICAO codes
from the OurAirports public dataset.
"""

import csv
import io
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"


class Command(BaseCommand):
    help = "Enrich airports_simple.csv with ICAO codes from OurAirports dataset"

    def handle(self, *args, **options):
        csv_path = Path(settings.BASE_DIR) / "trips" / "data" / "airports_simple.csv"

        self.stdout.write("Downloading OurAirports dataset...")
        response = requests.get(OURAIRPORTS_URL, timeout=30)
        response.raise_for_status()
        content = response.text

        # Build IATA → ICAO lookup from OurAirports
        iata_to_icao = {}
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            iata = row.get("iata_code", "").strip()
            icao = row.get("icao_code", "").strip()
            if iata and icao:
                iata_to_icao[iata.upper()] = icao.upper()

        self.stdout.write(f"Loaded {len(iata_to_icao)} IATA→ICAO mappings.")

        # Read existing CSV
        with open(csv_path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        matched = 0
        for row in rows:
            iata = row.get("iata_code", "").strip().upper()
            row["icao_code"] = iata_to_icao.get(iata, "")
            if row["icao_code"]:
                matched += 1

        # Write enriched CSV
        fieldnames = ["iata_code", "icao_code", "name", "city", "latitude", "longitude"]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {matched}/{len(rows)} airports enriched with ICAO code."
            )
        )
