from unittest.mock import MagicMock, patch

import pytest
import requests
from django.core.cache import cache

from trips.services import (
    GooglePlacesClient,
    GooglePlacesError,
    PlaceDetails,
    PlaceFullDetails,
    PlaceResult,
)

pytestmark = pytest.mark.django_db


SEARCH_RESPONSE = {
    "places": [
        {
            "id": "ChIJ_place_123",
            "displayName": {"text": "Museo Egizio"},
            "formattedAddress": "Via Accademia delle Scienze, 6, Torino",
            "location": {"latitude": 45.0687, "longitude": 7.6847},
        }
    ]
}

DETAILS_RESPONSE = {
    "websiteUri": "https://museoegizio.it",
    "internationalPhoneNumber": "+39 011 561 7776",
    "regularOpeningHours": {
        "periods": [
            {
                "open": {"day": 2, "hour": 9, "minute": 0},
                "close": {"day": 2, "hour": 19, "minute": 0},
            },
        ]
    },
}

PLACE_ID_RESPONSE = {"places": [{"id": "ChIJ_place_123"}]}
EMPTY_RESPONSE = {"places": []}


@pytest.fixture
def client():
    return GooglePlacesClient()


class TestGooglePlacesClientSearchText:
    def setup_method(self):
        cache.clear()

    def test_returns_place_results(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = SEARCH_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            results = client.search_text("museo egizio torino")

        assert len(results) == 1
        r = results[0]
        assert isinstance(r, PlaceResult)
        assert r.place_id == "ChIJ_place_123"
        assert r.name == "Museo Egizio"
        assert r.lat == 45.0687
        assert r.lng == 7.6847

        call_args = mock_post.call_args
        assert call_args.kwargs["headers"]["X-Goog-Api-Key"] == "test-key"
        assert "places.id" in call_args.kwargs["headers"]["X-Goog-FieldMask"]
        assert "places.location" in call_args.kwargs["headers"]["X-Goog-FieldMask"]

    def test_returns_empty_list_when_no_results(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = EMPTY_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp):
            results = client.search_text("ristorante inesistente")

        assert results == []

    def test_raises_on_missing_api_key(self, settings):
        settings.GOOGLE_PLACES_API_KEY = ""
        c = GooglePlacesClient()
        with pytest.raises(GooglePlacesError, match="not configured"):
            c.search_text("query")

    def test_raises_on_timeout(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        with patch(
            "trips.services.requests.post", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(GooglePlacesError, match="timed out"):
                client.search_text("query")

    def test_raises_on_request_exception(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_err = requests.RequestException("network error")
        mock_err.response = None
        with patch("trips.services.requests.post", side_effect=mock_err):
            with pytest.raises(GooglePlacesError, match="API error"):
                client.search_text("query")

    def test_respects_max_results(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = EMPTY_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            client.search_text("query", max_results=5)

        payload = mock_post.call_args.kwargs["json"]
        assert payload["maxResultCount"] == 5

    def test_sends_location_bias_when_provided(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = EMPTY_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            client.search_text("query", location_bias=(45.07, 7.68, 5000.0))

        payload = mock_post.call_args.kwargs["json"]
        assert "locationBias" in payload
        assert payload["locationBias"]["circle"]["center"]["latitude"] == 45.07
        assert payload["locationBias"]["circle"]["center"]["longitude"] == 7.68
        assert payload["locationBias"]["circle"]["radius"] == 5000.0


class TestGooglePlacesClientGetDetails:
    def setup_method(self):
        cache.clear()

    def test_returns_place_details(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = DETAILS_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp):
            details = client.get_place_details("ChIJ_place_123")

        assert isinstance(details, PlaceDetails)
        assert details.place_id == "ChIJ_place_123"
        assert details.website == "https://museoegizio.it"
        assert details.phone_number == "+39 011 561 7776"
        assert details.opening_hours is not None
        assert "tuesday" in details.opening_hours

    def test_returns_empty_strings_when_fields_missing(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp):
            details = client.get_place_details("ChIJ_place_123")

        assert details.website == ""
        assert details.phone_number == ""
        assert details.opening_hours is None

    def test_raises_on_missing_api_key(self, settings):
        settings.GOOGLE_PLACES_API_KEY = ""
        c = GooglePlacesClient()
        with pytest.raises(GooglePlacesError, match="not configured"):
            c.get_place_details("some-id")

    def test_raises_on_timeout(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        with patch(
            "trips.services.requests.get", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(GooglePlacesError, match="timed out"):
                client.get_place_details("some-id")

    def test_raises_on_request_exception(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_err = requests.RequestException("network error")
        mock_err.response = None
        with patch("trips.services.requests.get", side_effect=mock_err):
            with pytest.raises(GooglePlacesError, match="API error"):
                client.get_place_details("some-id")

    def test_raises_on_request_exception_with_response(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_response = MagicMock()
        mock_response.text = "Forbidden"
        mock_err = requests.RequestException("forbidden")
        mock_err.response = mock_response
        with patch("trips.services.requests.get", side_effect=mock_err):
            with pytest.raises(GooglePlacesError, match="Forbidden"):
                client.get_place_details("some-id")


class TestGooglePlacesClientSearchPlaceId:
    def setup_method(self):
        cache.clear()

    def test_returns_place_id(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = PLACE_ID_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp):
            place_id = client.search_place_id("museo egizio")

        assert place_id == "ChIJ_place_123"

    def test_returns_none_when_no_results(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = EMPTY_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp):
            place_id = client.search_place_id("inesistente")

        assert place_id is None

    def test_raises_on_timeout(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        with patch(
            "trips.services.requests.post", side_effect=requests.exceptions.Timeout
        ):
            with pytest.raises(GooglePlacesError, match="timed out"):
                client.search_place_id("query")

    def test_raises_on_request_exception(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_err = requests.RequestException("network error")
        mock_err.response = None
        with patch("trips.services.requests.post", side_effect=mock_err):
            with pytest.raises(GooglePlacesError, match="API error"):
                client.search_place_id("query")

    def test_raises_on_missing_api_key(self, settings):
        settings.GOOGLE_PLACES_API_KEY = ""
        c = GooglePlacesClient()
        with pytest.raises(GooglePlacesError, match="not configured"):
            c.search_place_id("query")

    def test_requests_only_id_field(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = PLACE_ID_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            client.search_place_id("query")

        assert mock_post.call_args.kwargs["headers"]["X-Goog-FieldMask"] == "places.id"


class TestGooglePlacesClientCache:
    def setup_method(self):
        cache.clear()

    def test_search_place_id_cached_on_second_call(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = PLACE_ID_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            result1 = client.search_place_id("museo egizio")
            result2 = client.search_place_id("museo egizio")

        assert result1 == result2 == "ChIJ_place_123"
        assert mock_post.call_count == 1

    def test_search_place_id_different_queries_both_hit_api(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = PLACE_ID_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            client.search_place_id("museo egizio")
            client.search_place_id("colosseo")

        assert mock_post.call_count == 2

    def test_search_place_id_none_result_not_cached(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = EMPTY_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            client.search_place_id("inesistente")
            client.search_place_id("inesistente")

        assert mock_post.call_count == 2

    def test_get_place_details_cached_on_second_call(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = DETAILS_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp) as mock_get:
            d1 = client.get_place_details("ChIJ_place_123")
            d2 = client.get_place_details("ChIJ_place_123")

        assert d1.website == d2.website == "https://museoegizio.it"
        assert mock_get.call_count == 1

    def test_get_place_details_different_ids_both_hit_api(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = DETAILS_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp) as mock_get:
            client.get_place_details("place_aaa")
            client.get_place_details("place_bbb")

        assert mock_get.call_count == 2

    def test_search_text_cached_on_second_call(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = SEARCH_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            r1 = client.search_text("museo egizio")
            r2 = client.search_text("museo egizio")

        assert len(r1) == len(r2) == 1
        assert mock_post.call_count == 1

    def test_search_text_different_bias_both_hit_api(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = SEARCH_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            client.search_text("query", location_bias=(45.0, 7.0, 1000.0))
            client.search_text("query", location_bias=(48.0, 2.0, 1000.0))

        assert mock_post.call_count == 2

    def test_search_text_with_language_code(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = SEARCH_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.post", return_value=mock_resp) as mock_post:
            results = client.search_text("museo egizio", language_code="it")

        assert len(results) == 1
        payload = mock_post.call_args.kwargs["json"]
        assert payload["languageCode"] == "it"


FULL_DETAILS_RESPONSE = {
    "displayName": {"text": "Museo Egizio"},
    "formattedAddress": "Via Accademia delle Scienze 6, 10123 Torino TO, Italia",
    "addressComponents": [
        {"types": ["locality"], "longText": "Torino"},
        {"types": ["country"], "longText": "Italia"},
    ],
    "location": {"latitude": 45.0687, "longitude": 7.6847},
    "websiteUri": "https://museoegizio.it",
    "internationalPhoneNumber": "+39 011 561 7776",
    "regularOpeningHours": {
        "periods": [
            {
                "open": {"day": 2, "hour": 9, "minute": 0},
                "close": {"day": 2, "hour": 19, "minute": 0},
            },
        ]
    },
}


class TestGooglePlacesClientGetFullDetails:
    def setup_method(self):
        cache.clear()

    def test_returns_full_place_details(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = FULL_DETAILS_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp):
            result = client.get_full_place_details("ChIJ_place_123")

        assert isinstance(result, PlaceFullDetails)
        assert result.name == "Museo Egizio"
        assert (
            result.address == "Via Accademia delle Scienze 6, 10123 Torino TO, Italia"
        )
        assert result.city == "Torino"
        assert result.lat == 45.0687
        assert result.lng == 7.6847
        assert result.website == "https://museoegizio.it"
        assert result.phone_number == "+39 011 561 7776"
        assert result.opening_hours is not None

    def test_extracts_city_from_locality_component(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            **FULL_DETAILS_RESPONSE,
            "addressComponents": [
                {"types": ["country"], "longText": "Italia"},
                {"types": ["locality"], "longText": "Milano"},
            ],
        }
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp):
            result = client.get_full_place_details("ChIJ_place_456")

        assert result.city == "Milano"

    def test_city_empty_when_no_locality_component(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            **FULL_DETAILS_RESPONSE,
            "addressComponents": [{"types": ["country"], "longText": "Italia"}],
        }
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp):
            result = client.get_full_place_details("ChIJ_place_789")

        assert result.city == ""

    def test_raises_on_missing_api_key(self, settings):
        settings.GOOGLE_PLACES_API_KEY = ""
        with pytest.raises(GooglePlacesError, match="not configured"):
            GooglePlacesClient().get_full_place_details("ChIJ_place_123")

    def test_raises_on_timeout(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        with patch(
            "trips.services.requests.get",
            side_effect=requests.exceptions.Timeout,
        ):
            with pytest.raises(GooglePlacesError, match="timed out"):
                client.get_full_place_details("ChIJ_place_123")

    def test_raises_on_request_exception(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        exc = requests.RequestException("connection error")
        exc.response = None
        with patch("trips.services.requests.get", side_effect=exc):
            with pytest.raises(GooglePlacesError, match="API error"):
                client.get_full_place_details("ChIJ_place_123")

    def test_raises_on_request_exception_with_response(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        exc = requests.RequestException("bad request")
        exc.response = MagicMock()
        exc.response.text = "INVALID_REQUEST"
        with patch("trips.services.requests.get", side_effect=exc):
            with pytest.raises(GooglePlacesError, match="INVALID_REQUEST"):
                client.get_full_place_details("ChIJ_place_123")

    def test_cached_on_second_call(self, client, settings):
        settings.GOOGLE_PLACES_API_KEY = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = FULL_DETAILS_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("trips.services.requests.get", return_value=mock_resp) as mock_get:
            r1 = client.get_full_place_details("ChIJ_cached_123")
            r2 = client.get_full_place_details("ChIJ_cached_123")

        assert r1.name == r2.name == "Museo Egizio"
        assert mock_get.call_count == 1
