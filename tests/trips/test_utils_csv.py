"""Tests for CSV loading edge cases in utils"""

import csv

import pytest

pytestmark = pytest.mark.django_db


def test_load_train_stations_skips_missing_coordinates(tmp_path):
    """Test that stations without coordinates are skipped"""
    import trips.utils

    # Reset cache
    trips.utils._STATIONS_CACHE = None

    # Create temporary CSV with missing coordinates
    csv_dir = tmp_path / "trips" / "data"
    csv_dir.mkdir(parents=True)
    csv_file = csv_dir / "stations_simplified.csv"

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "latitude", "longitude", "country"]
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "id": "1",
                    "name": "Valid Station",
                    "latitude": "45.5",
                    "longitude": "9.2",
                    "country": "Italy",
                },
                {
                    "id": "2",
                    "name": "No Coordinates",
                    "latitude": "",
                    "longitude": "",
                    "country": "Italy",
                },
                {
                    "id": "3",
                    "name": "Missing Lat",
                    "latitude": "",
                    "longitude": "9.2",
                    "country": "Italy",
                },
            ]
        )

    # Temporarily change BASE_DIR
    from django.conf import settings

    original_base_dir = settings.BASE_DIR
    settings.BASE_DIR = tmp_path

    try:
        from trips.utils import load_train_stations

        stations = load_train_stations()

        # Should only load the valid station
        assert len(stations) == 1
        assert stations[0]["name"] == "Valid Station"
    finally:
        settings.BASE_DIR = original_base_dir
        trips.utils._STATIONS_CACHE = None


def test_load_train_stations_handles_invalid_data(tmp_path):
    """Test that invalid CSV data is handled gracefully"""
    import trips.utils

    # Reset cache
    trips.utils._STATIONS_CACHE = None

    # Create temporary CSV with invalid data
    csv_dir = tmp_path / "trips" / "data"
    csv_dir.mkdir(parents=True)
    csv_file = csv_dir / "stations_simplified.csv"

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "latitude", "longitude", "country"]
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "id": "1",
                    "name": "Valid Station",
                    "latitude": "45.5",
                    "longitude": "9.2",
                    "country": "Italy",
                },
                {
                    "id": "2",
                    "name": "Invalid Lat",
                    "latitude": "not_a_number",
                    "longitude": "9.2",
                    "country": "Italy",
                },
                {
                    "id": "3",
                    "name": "Invalid Lon",
                    "latitude": "45.5",
                    "longitude": "not_a_number",
                    "country": "Italy",
                },
            ]
        )

    # Temporarily change BASE_DIR
    from django.conf import settings

    original_base_dir = settings.BASE_DIR
    settings.BASE_DIR = tmp_path

    try:
        from trips.utils import load_train_stations

        stations = load_train_stations()

        # Should only load the valid station (invalid ones skipped)
        assert len(stations) == 1
        assert stations[0]["name"] == "Valid Station"
        assert isinstance(stations[0]["latitude"], float)
        assert isinstance(stations[0]["longitude"], float)
    finally:
        settings.BASE_DIR = original_base_dir
        trips.utils._STATIONS_CACHE = None
