import time
from unittest.mock import patch

import pytest
from django.core.cache import cache

from tests.test import TestCase
from trips.utils import generate_cache_key, geocode_location

pytestmark = pytest.mark.django_db


class RateLimitCheckTests(TestCase):
    def test_rate_limit_check_waits_if_called_too_soon(self):
        """Should sleep if called within 1 second of last request."""

        from trips.utils import rate_limit_check

        cache.set("nominatim_last_request_time", time.time(), 60)
        start = time.time()
        rate_limit_check()
        elapsed = time.time() - start
        assert elapsed >= 0.99  # Should wait at least ~1 second

    def test_rate_limit_check_no_wait_if_enough_time_passed(self):
        """Should not sleep if more than 1 second has passed since last request."""

        from trips.utils import rate_limit_check

        cache.set("nominatim_last_request_time", time.time() - 2, 60)
        start = time.time()
        rate_limit_check()
        elapsed = time.time() - start
        assert elapsed < 0.5  # Should not wait


class GenerateCacheKeyTests(TestCase):
    def test_generate_cache_key_basic(self):
        key = generate_cache_key("Hotel Milano", "Milan")
        assert key.startswith("geocode_")
        assert len(key) < 100  # Should not be excessively long

    def test_generate_cache_key_empty(self):
        key = generate_cache_key("", "")
        assert key.startswith("geocode_")
        assert len(key) < 100  # Should not be excessively long


class GeocodeLocationTests(TestCase):
    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_sorted_addresses(self, mock_get):
        from trips.utils import geocode_location

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "address": {"road": "Via Roma", "city": "Rome"},
                "lat": "41.9028",
                "lon": "12.4964",
                "importance": 0.7,
                "place_rank": 30,
                "name": "Hotel Roma",
            },
            {
                "address": {"road": "Via Milano", "city": "Milan"},
                "lat": "45.4642",
                "lon": "9.19",
                "importance": 0.9,
                "place_rank": 30,
                "name": "Hotel Milano",
            },
        ]
        addresses = geocode_location("Hotel", "Italy")
        assert len(addresses) == 2
        # Should be sorted by importance descending
        assert addresses[0]["address"].endswith("Milan")
        assert addresses[1]["address"].endswith("Rome")

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_empty_on_no_results(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}
        addresses = geocode_location("Nonexistent", "Nowhere")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("API error")
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_empty_list_response(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []  # Simulate API returns empty list
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_non_200_status_code(self, mock_get):
        """Should return [] if API response status code is not 200."""
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = [
            {
                "address": {"road": "Via Roma", "city": "Rome"},
                "lat": "41.9028",
                "lon": "12.4964",
                "importance": 0.7,
                "place_rank": 30,
                "name": "Hotel Roma",
            }
        ]
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    def test_geocode_location_returns_none_if_name_or_city_missing(self):
        assert geocode_location("", "Rome") is None
        assert geocode_location("Hotel", "") is None

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_cached_result(self, mock_get):
        # Prepare a fake cached result
        cached_result = [
            {
                "address": "Via Roma 1, Rome",
                "lat": 41.9028,
                "lon": 12.4964,
                "importance": 0.7,
                "place_rank": 30,
            }
        ]
        key = generate_cache_key("Hotel Roma", "Rome")
        cache.set(key, cached_result, 60)
        # Should return cached result and not call requests.get
        addresses = geocode_location("Hotel Roma", "Rome")
        assert addresses == cached_result
        assert not mock_get.called


class GeocodeLocationAddressFormatTests(TestCase):
    def test_address_format_with_only_street_and_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"road": "Via Milano", "city": "Milan"},
                    "lat": "45.4642",
                    "lon": "9.19",
                    "importance": 0.9,
                    "place_rank": 30,
                    "name": "Hotel Milano",
                }
            ]
            addresses = geocode_location("Hotel Milano", "Milan")
            assert addresses[0]["address"] == "Via Milano, Milan"

    def test_address_format_with_street_housenumber_and_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {
                        "road": "Via Roma",
                        "house_number": "1",
                        "city": "Rome",
                    },
                    "lat": "41.9028",
                    "lon": "12.4964",
                    "importance": 0.7,
                    "place_rank": 30,
                    "name": "Hotel Roma",
                }
            ]
            addresses = geocode_location("Hotel Roma", "Rome")
            assert addresses[0]["address"] == "Via Roma 1, Rome"

    def test_address_format_with_only_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"city": "Naples"},
                    "lat": "40.8522",
                    "lon": "14.2681",
                    "importance": 0.5,
                    "place_rank": 30,
                    "name": "Napoli",
                }
            ]
            addresses = geocode_location("Napoli", "Naples")
            assert addresses[0]["address"] == "Naples"

    def test_address_format_with_street_housenumber_no_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"road": "Via Firenze", "house_number": "22"},
                    "lat": "43.7696",
                    "lon": "11.2558",
                    "importance": 0.6,
                    "place_rank": 30,
                    "name": "Hotel Firenze",
                }
            ]
            addresses = geocode_location("Hotel Firenze", "Firenze")
            assert addresses[0]["address"] == "Via Firenze 22"


class SelectBestResultTests(TestCase):
    def test_select_best_result_returns_none_for_empty(self):
        from trips.utils import select_best_result

        assert select_best_result([], "Hotel", "Rome") is None

    def test_select_best_result_prefers_city_and_name(self):
        from trips.utils import select_best_result

        results = [
            {
                "display_name": "Hotel Roma, Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.5,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
            {
                "display_name": "Hotel Milano, Milan, Italy",
                "address": {"city": "Milan"},
                "importance": 0.9,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
        ]
        best = select_best_result(results, "Hotel Roma", "Rome")
        assert best["address"]["city"] == "Rome"

    def test_select_best_result_penalizes_generic_place(self):
        from trips.utils import select_best_result

        results = [
            {
                "display_name": "Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.8,
                "place_rank": 20,
                "class": "place",
                "type": "city",
            },
            {
                "display_name": "Hotel Roma, Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.5,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
        ]
        best = select_best_result(results, "Hotel Roma", "Rome")
        assert best["class"] == "tourism"
        assert best["type"] == "hotel"

    def test_select_best_result_returns_first_if_no_scores(self):
        from trips.utils import select_best_result

        results = [
            {"display_name": "A", "address": {}, "importance": 0.1, "place_rank": 99},
            {"display_name": "B", "address": {}, "importance": 0.1, "place_rank": 99},
        ]
        best = select_best_result(results, "", "")
        assert best == results[0]
