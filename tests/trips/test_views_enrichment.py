import json
from unittest.mock import Mock, patch

import pytest
import requests
from django.test import override_settings

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    StayFactory,
    TripFactory,
)

pytestmark = pytest.mark.django_db


class SingleEventViewTest(TestCase):
    """Test cases for single_event view"""

    def test_get_single_event_success(self):
        """Test successful retrieval of a single event"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip)

        with self.login(user):
            response = self.get("trips:single-event", pk=event.pk)

        self.response_200(response)
        assert response.context["event"] == event


@patch("trips.views.requests.get")
@patch("trips.views.requests.post")
class EnrichEventViewTest(TestCase):
    """Test cases for enrich_event view"""

    def test_enrich_event_success(self, mock_post, mock_get):
        """Test successful enrichment of an event - returns preview"""
        # Mock Google Places API responses
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            "regularOpeningHours": {
                "periods": [
                    {
                        "open": {"day": 1, "hour": 9, "minute": 0},
                        "close": {"day": 1, "hour": 17, "minute": 0},
                    }
                ]
            },
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        # Event should NOT be saved yet (preview mode)
        event.refresh_from_db()
        assert event.place_id == ""
        assert event.enriched is False
        # Check that enriched_data is in context for preview
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["place_id"] == "test_place_id"
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert "monday" in response.context["enriched_data"]["opening_hours"]
        assert response.context["show_preview"] is True

    def test_enrich_event_success_no_opening_hours(self, mock_post, mock_get):
        """Test successful enrichment without opening hours"""
        # Mock Google Places API responses without opening hours
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            # No regularOpeningHours
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        # Check that enriched_data is in context without opening_hours
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert response.context["enriched_data"]["opening_hours"] is None
        assert "opening_hours_json" not in response.context["enriched_data"]
        assert response.context["show_preview"] is True

    def test_enrich_event_no_name_or_address(self, mock_post, mock_get):
        """Test enrichment with no name or address"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(day=day, trip=trip, name="", address="")

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert (
            response.context["error_message"]
            == "Event must have a name and an address to be enriched."
        )

    def test_enrich_event_no_api_key(self, mock_post, mock_get):
        """Test enrichment with no API key"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY=""):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API key is not configured."
            in response.context["error_message"]
        )

    def test_enrich_event_search_request_fails(self, mock_post, mock_get):
        """Test enrichment when search request fails"""
        mock_post.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_event_search_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when search request fails with a response"""
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_post.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_event_no_place_found(self, mock_post, mock_get):
        """Test enrichment when no place is found"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": []}

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "Could not find a matching place." in response.context["error_message"]

    def test_enrich_event_details_request_fails(self, mock_post, mock_get):
        """Test enrichment when details request fails"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_event_details_request_fails_with_response(
        self, mock_post, mock_get
    ):
        """Test enrichment when details request fails with a response"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_get.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_event_search_timeout(self, mock_post, mock_get):
        """Test enrichment when search request times out"""
        mock_post.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )

    def test_enrich_event_details_timeout(self, mock_post, mock_get):
        """Test enrichment when details request times out"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )


class ConfirmEnrichEventViewTest(TestCase):
    """Test cases for confirm_enrich_event view"""

    def test_confirm_enrich_event_success(self):
        """Test successful confirmation and saving of enriched data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": '{"monday": {"open": "9:00 AM", "close": "5:00 PM"}}',
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should return 200 with event detail view and HX-Trigger header
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == f"eventModified{event.pk}"
        assert "success_message" in response.context
        assert response.context["success_message"] == "Event enriched successfully!"

        # Event should be saved with enriched data
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.website == "https://example.com"
        assert event.phone_number == "+1234567890"
        assert event.opening_hours == {
            "monday": {"open": "9:00 AM", "close": "5:00 PM"}
        }
        assert event.enriched is True

    def test_confirm_enrich_event_no_opening_hours(self):
        """Test confirmation without opening_hours"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            # No opening_hours field
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == f"eventModified{event.pk}"
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.website == "https://example.com"
        assert event.phone_number == "+1234567890"
        assert event.opening_hours is None
        assert event.enriched is True

    def test_confirm_enrich_event_invalid_json(self):
        """Test confirmation with invalid opening_hours JSON"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": "invalid json",
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should still save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == f"eventModified{event.pk}"
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.opening_hours is None
        assert event.enriched is True

    def test_confirm_enrich_event_unauthorized(self):
        """Test confirmation by unauthorized user"""
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
        }

        with self.login(other_user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should return 404 for unauthorized access
        self.response_404(response)
        event.refresh_from_db()
        assert event.enriched is False


@patch("trips.views.requests.get")
@patch("trips.views.requests.post")
class EnrichStayViewTest(TestCase):
    """Test cases for enrich_stay view"""

    def test_enrich_stay_success(self, mock_post, mock_get):
        """Test successful enrichment of a stay - returns preview"""
        # Mock Google Places API responses
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            "regularOpeningHours": {
                "periods": [
                    {
                        "open": {"day": 1, "hour": 9, "minute": 0},
                        "close": {"day": 1, "hour": 17, "minute": 0},
                    }
                ]
            },
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        # Stay should NOT be saved yet (preview mode)
        stay.refresh_from_db()
        assert stay.place_id == ""
        assert stay.enriched is False
        # Check that enriched_data is in context for preview
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["place_id"] == "test_place_id"
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert "monday" in response.context["enriched_data"]["opening_hours"]
        assert response.context["show_preview"] is True

    def test_enrich_stay_no_name_or_address(self, mock_post, mock_get):
        """Test enrichment with no name or address"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="", address="")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert (
            response.context["error_message"]
            == "Stay must have a name and an address to be enriched."
        )

    def test_enrich_stay_no_api_key(self, mock_post, mock_get):
        """Test enrichment with no API key"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY=""):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)
        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API key is not configured."
            in response.context["error_message"]
        )

    def test_enrich_stay_search_request_fails(self, mock_post, mock_get):
        """Test enrichment when search request fails"""
        mock_post.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_stay_search_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when search request fails with a response"""
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_post.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_stay_no_place_found(self, mock_post, mock_get):
        """Test enrichment when no place is found"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": []}

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "Could not find a matching place." in response.context["error_message"]

    def test_enrich_stay_details_request_fails(self, mock_post, mock_get):
        """Test enrichment when details request fails"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_stay_details_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when details request fails with a response"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_get.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_stay_search_timeout(self, mock_post, mock_get):
        """Test enrichment when search request times out"""
        mock_post.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )

    def test_enrich_stay_details_timeout(self, mock_post, mock_get):
        """Test enrichment when details request times out"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )

    def test_enrich_stay_success_no_opening_hours(self, mock_post, mock_get):
        """Test successful enrichment without opening hours"""
        # Mock Google Places API responses without opening hours
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            # No regularOpeningHours
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        # Check that enriched_data is in context without opening_hours
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert response.context["enriched_data"]["opening_hours"] is None
        assert "opening_hours_json" not in response.context["enriched_data"]
        assert response.context["show_preview"] is True


class ConfirmEnrichStayViewTest(TestCase):
    """Test cases for confirm_enrich_stay view"""

    def test_confirm_enrich_stay_success(self):
        """Test successful confirmation and saving of enriched data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": '{"monday": {"open": "9:00 AM", "close": "5:00 PM"}}',
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should return 200 with stay detail view and HX-Trigger header
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        # Check that it triggers update for the day
        triggers = json.loads(response.headers["HX-Trigger"])
        assert f"dayModified{day.pk}" in triggers
        assert "success_message" in response.context
        assert response.context["success_message"] == "Stay enriched successfully!"

        # Stay should be saved with enriched data
        stay.refresh_from_db()
        assert stay.place_id == "test_place_id"
        assert stay.website == "https://example.com"
        assert stay.phone_number == "+1234567890"
        assert stay.opening_hours == {"monday": {"open": "9:00 AM", "close": "5:00 PM"}}
        assert stay.enriched is True

    def test_confirm_enrich_stay_no_opening_hours(self):
        """Test confirmation without opening_hours"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            # No opening_hours field
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        # Check that it triggers update for the day
        triggers = json.loads(response.headers["HX-Trigger"])
        assert f"dayModified{day.pk}" in triggers
        stay.refresh_from_db()
        assert stay.place_id == "test_place_id"
        assert stay.website == "https://example.com"
        assert stay.phone_number == "+1234567890"
        assert stay.opening_hours is None
        assert stay.enriched is True

    def test_confirm_enrich_stay_invalid_json(self):
        """Test confirmation with invalid opening_hours JSON"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": "invalid json",
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should still save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        # Check that it triggers update for the day
        triggers = json.loads(response.headers["HX-Trigger"])
        assert f"dayModified{day.pk}" in triggers
        stay.refresh_from_db()
        assert stay.place_id == "test_place_id"
        assert stay.opening_hours is None
        assert stay.enriched is True

    def test_confirm_enrich_stay_unauthorized(self):
        """Test confirmation by unauthorized user"""
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
        }

        with self.login(other_user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should return 404 for unauthorized access
        self.response_404(response)
        stay.refresh_from_db()
        assert stay.enriched is False
