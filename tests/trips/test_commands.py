"""Tests for management commands"""

import csv
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


class TestGeocodeStationsCommand:
    """Test geocode_stations management command"""

    @pytest.fixture
    def mock_csv_file(self, tmp_path):
        """Create a temporary CSV file with test data"""
        csv_file = tmp_path / "stations_simplified.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "name", "latitude", "longitude", "country"],
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            writer.writerows(
                [
                    {
                        "id": "1",
                        "name": "Rome Termini",
                        "latitude": "",
                        "longitude": "",
                        "country": "Italy",
                    },
                    {
                        "id": "2",
                        "name": "Milan Central",
                        "latitude": "",
                        "longitude": "",
                        "country": "Italy",
                    },
                    {
                        "id": "3",
                        "name": "Paris Gare de Lyon",
                        "latitude": "48.8446",
                        "longitude": "2.3736",
                        "country": "France",
                    },
                ]
            )
        return csv_file

    def test_csv_not_found(self):
        """Test command fails gracefully when CSV file doesn't exist"""
        out = StringIO()
        with patch(
            "trips.management.commands.geocode_stations.Path"
        ) as mock_path_class:
            # Mock the entire chain: Path(settings.BASE_DIR) / "trips" / "data" / "stations_simplified.csv"
            mock_csv_path = Mock(spec=Path)
            mock_csv_path.exists.return_value = False
            mock_path_class.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_csv_path
            call_command("geocode_stations", stdout=out)
            assert "CSV file not found" in out.getvalue()

    def test_dry_run_mode(self, mock_csv_file, tmp_path):
        """Test dry run mode shows stations without geocoding"""
        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy mock CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(mock_csv_file, final_csv)

        out = StringIO()
        with patch(
            "trips.management.commands.geocode_stations.settings.BASE_DIR", base_dir
        ):
            call_command("geocode_stations", "--dry-run", stdout=out)
            output = out.getvalue()
            assert "DRY RUN" in output
            assert "Found 2 stations without coordinates" in output
            assert "Rome Termini" in output

    def test_limit_option(self, mock_csv_file, tmp_path):
        """Test limit option restricts number of stations"""
        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy mock CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(mock_csv_file, final_csv)

        out = StringIO()
        with patch(
            "trips.management.commands.geocode_stations.settings.BASE_DIR", base_dir
        ):
            call_command("geocode_stations", "--dry-run", "--limit", "1", stdout=out)
            output = out.getvalue()
            assert "Limited to 1 stations for geocoding" in output

    @patch("trips.management.commands.geocode_stations.geocoder.mapbox")
    @patch("trips.management.commands.geocode_stations.time.sleep")
    @patch("trips.management.commands.geocode_stations.settings")
    def test_successful_geocoding(
        self, mock_settings, mock_sleep, mock_geocoder, mock_csv_file, tmp_path
    ):
        """Test successful geocoding updates CSV"""
        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy mock CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(mock_csv_file, final_csv)

        # Configure mocked settings
        mock_settings.BASE_DIR = base_dir
        mock_settings.MAPBOX_ACCESS_TOKEN = "test_token"  # nosec B105

        # Mock geocoder response
        mock_result = Mock()
        mock_result.latlng = [41.9009, 12.5028]
        mock_geocoder.return_value = mock_result

        out = StringIO()
        call_command("geocode_stations", "--limit", "1", stdout=out)
        output = out.getvalue()
        assert "Successfully geocoded" in output
        assert "41.9009" in output

        # Verify CSV was updated
        with open(final_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]["latitude"] == "41.9009"
            assert rows[0]["longitude"] == "12.5028"

    @patch("trips.management.commands.geocode_stations.geocoder.mapbox")
    @patch("trips.management.commands.geocode_stations.time.sleep")
    @patch("trips.management.commands.geocode_stations.settings")
    def test_geocoding_failure(
        self, mock_settings, mock_sleep, mock_geocoder, mock_csv_file, tmp_path
    ):
        """Test geocoding failure is handled gracefully"""
        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy mock CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(mock_csv_file, final_csv)

        # Configure mocked settings
        mock_settings.BASE_DIR = base_dir
        mock_settings.MAPBOX_ACCESS_TOKEN = "test_token"  # nosec B105

        # Mock geocoder with no results
        mock_result = Mock()
        mock_result.latlng = None
        mock_geocoder.return_value = mock_result

        out = StringIO()
        call_command("geocode_stations", "--limit", "1", stdout=out)
        output = out.getvalue()
        assert "Failed to geocode" in output
        assert "No results" in output

    @patch("trips.management.commands.geocode_stations.geocoder.mapbox")
    @patch("trips.management.commands.geocode_stations.time.sleep")
    @patch("trips.management.commands.geocode_stations.settings")
    def test_geocoding_exception(
        self, mock_settings, mock_sleep, mock_geocoder, mock_csv_file, tmp_path
    ):
        """Test geocoding exception is handled gracefully"""
        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy mock CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(mock_csv_file, final_csv)

        # Configure mocked settings
        mock_settings.BASE_DIR = base_dir
        mock_settings.MAPBOX_ACCESS_TOKEN = "test_token"  # nosec B105

        # Mock geocoder raising exception
        mock_geocoder.side_effect = Exception("API Error")

        out = StringIO()
        call_command("geocode_stations", "--limit", "1", stdout=out)
        output = out.getvalue()
        assert "Error geocoding" in output
        assert "API Error" in output

    def test_custom_delay(self, mock_csv_file, tmp_path):
        """Test custom delay parameter"""
        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy mock CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(mock_csv_file, final_csv)

        out = StringIO()
        with patch(
            "trips.management.commands.geocode_stations.settings.BASE_DIR", base_dir
        ):
            # Just verify command accepts delay parameter
            call_command("geocode_stations", "--dry-run", "--delay", "0.5", stdout=out)
            assert "DRY RUN" in out.getvalue()

    def test_dry_run_with_many_stations(self, tmp_path):
        """Test dry run shows 'and X more' message when >10 stations"""
        # Create CSV with 15 stations without coordinates
        csv_file = tmp_path / "stations.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "name", "latitude", "longitude", "country"],
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            for i in range(15):
                writer.writerow(
                    {
                        "id": str(i + 1),
                        "name": f"Station {i + 1}",
                        "latitude": "",
                        "longitude": "",
                        "country": "Italy",
                    }
                )

        # Create proper directory structure
        base_dir = tmp_path / "project"
        csv_dir = base_dir / "trips" / "data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Copy CSV to proper location
        import shutil

        final_csv = csv_dir / "stations_simplified.csv"
        shutil.copy(csv_file, final_csv)

        out = StringIO()
        with patch(
            "trips.management.commands.geocode_stations.settings.BASE_DIR", base_dir
        ):
            call_command("geocode_stations", "--dry-run", stdout=out)
            output = out.getvalue()
            assert "DRY RUN" in output
            assert "Found 15 stations without coordinates" in output
            assert "... and 5 more" in output  # 15 - 10 = 5
