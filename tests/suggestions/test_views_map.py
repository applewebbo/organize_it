from unittest.mock import MagicMock, patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.schemas import Suggestion
from suggestions.services import GroundedSuggestion
from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import Event, Stay
from trips.services import GooglePlacesError, PlaceFullDetails

pytestmark = pytest.mark.django_db

MOCK_GEO = MagicMock()
MOCK_GEO.latlng = None


def _grounded(kind, name, type_value=None):
    return GroundedSuggestion(
        suggestion=Suggestion(
            kind=kind, name=name, description="nice", type=type_value
        ),
        address="Via Roma 1, Roma",
        city="Roma",
        latitude=41.9,
        longitude=12.5,
        place_id=f"place_{name}",
    )


class TestGenerateView(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        response = self.post("suggestions:generate", pk=trip.pk)
        self.response_302(response)

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.post("suggestions:generate", pk=trip.pk)
        self.response_404(response)

    def test_get_not_allowed(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("suggestions:generate", pk=trip.pk)
        assert response.status_code == 405

    @patch("suggestions.views.generate_suggestions")
    def test_renders_cards(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = [
            _grounded("experience", "Colosseo", 1),
            _grounded("meal", "Trattoria", 3),
            _grounded("stay", "Hotel"),
        ]
        with self.login(user):
            response = self.post(
                "suggestions:generate", pk=trip.pk, data={"notes": "with kids"}
            )
        self.response_200(response)
        content = response.content.decode()
        assert "Colosseo" in content
        assert "Trattoria" in content
        assert "Hotel" in content
        # per-trip notes forwarded as overrides
        _, kwargs = mock_generate.call_args
        args = mock_generate.call_args.args
        assert args[2] == {"notes": "with kids"}

    @patch("suggestions.views.generate_suggestions")
    def test_config_error_shows_settings_link(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.side_effect = AISuggestionError(
            "boom", kind=AISuggestionError.CONFIG
        )
        with self.login(user):
            response = self.post("suggestions:generate", pk=trip.pk)
        self.response_200(response)
        content = response.content.decode()
        assert "/accounts/profile/" in content
        assert "not configured" in content

    @patch("suggestions.views.generate_suggestions")
    def test_quota_error_message(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.side_effect = AISuggestionError(
            "429", kind=AISuggestionError.QUOTA
        )
        with self.login(user):
            response = self.post("suggestions:generate", pk=trip.pk)
        self.response_200(response)
        content = response.content.decode()
        assert "usage limit" in content
        assert "/accounts/profile/" not in content

    @patch("suggestions.views.generate_suggestions")
    def test_generic_error_message(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.side_effect = AISuggestionError("boom")
        with self.login(user):
            response = self.post("suggestions:generate", pk=trip.pk)
        self.response_200(response)
        content = response.content.decode()
        assert "Something went wrong" in content
        assert "/accounts/profile/" not in content

    @patch("suggestions.views.generate_suggestions")
    def test_no_suggestions(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = []
        with self.login(user):
            response = self.post("suggestions:generate", pk=trip.pk)
        self.response_200(response)
        assert "No suggestions found" in response.content.decode()


class TestDetailsView(TestCase):
    @patch("suggestions.views.GooglePlacesClient")
    def test_returns_place_details(self, mock_client):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_client.return_value.get_full_place_details.return_value = PlaceFullDetails(
            place_id="p1", website="https://x.test", phone_number="+39 06 1234"
        )
        with self.login(user):
            response = self.get(
                "suggestions:details", pk=trip.pk, data={"place_id": "p1"}
            )
        self.response_200(response)
        assert "https://x.test" in response.content.decode()

    @patch("suggestions.views.GooglePlacesClient")
    def test_details_api_error(self, mock_client):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_client.return_value.get_full_place_details.side_effect = GooglePlacesError(
            "boom"
        )
        with self.login(user):
            response = self.get(
                "suggestions:details", pk=trip.pk, data={"place_id": "p1"}
            )
        self.response_200(response)
        assert "boom" in response.content.decode()

    def test_details_without_place_id(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("suggestions:details", pk=trip.pk)
        self.response_200(response)

    def test_details_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("suggestions:details", pk=trip.pk)
        self.response_404(response)


class TestModalView(TestCase):
    def test_renders_modal(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("suggestions:modal", pk=trip.pk)
        self.response_200(response)
        assert 'name="context"' in response.content.decode()

    def test_modal_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("suggestions:modal", pk=trip.pk)
        self.response_404(response)

    @patch("suggestions.views.generate_suggestions")
    def test_generate_modal_uses_accept_endpoints(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = [_grounded("experience", "Colosseo", 1)]
        with self.login(user):
            response = self.post(
                "suggestions:generate",
                pk=trip.pk,
                data={"context": "modal", "refresh": "1"},
            )
        self.response_200(response)
        assert (
            f"/suggestions/trip/{trip.pk}/accept/experience/"
            in response.content.decode()
        )
        # refresh flag forwarded as force_refresh
        assert mock_generate.call_args.args[4] is True


class TestAcceptViews(TestCase):
    def _post(self, user, trip, kind, data):
        with self.login(user):
            return self.post(f"suggestions:accept-{kind}", pk=trip.pk, data=data)

    def test_accept_experience_creates_orphaned_event(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        response = self._post(
            user,
            trip,
            "experience",
            {
                "name": "Colosseo",
                "address": "Piazza del Colosseo",
                "google_place_id": "p1",
                "lat": "41.9",
                "lng": "12.5",
            },
        )
        self.response_200(response)
        assert response["HX-Trigger"] == "unpairedModified"
        event = Event.objects.get(trip=trip, name="Colosseo")
        assert event.category == Event.Category.EXPERIENCE
        assert event.day is None
        assert event.latitude == 41.9

    def test_accept_meal_creates_event(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        self._post(
            user, trip, "meal", {"name": "Trattoria", "lat": "41.9", "lng": "12.5"}
        )
        event = Event.objects.get(trip=trip, name="Trattoria")
        assert event.category == Event.Category.MEAL

    def test_accept_replaces_card_with_success_message(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        response = self._post(user, trip, "experience", {"name": "Colosseo"})
        content = response.content.decode()
        assert "Added to your trip" in content
        # modal context (no context field): no out-of-band events panel refresh
        assert "hx-swap-oob" not in content

    def test_accept_map_context_refreshes_events_panel(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        response = self._post(
            user, trip, "experience", {"name": "Colosseo", "context": "map"}
        )
        content = response.content.decode()
        assert 'id="events-panel"' in content
        assert "hx-swap-oob" in content

    def test_accept_stay_creates_stay(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        self._post(
            user,
            trip,
            "stay",
            {"name": "Hotel Roma", "lat": "41.9", "lng": "12.5"},
        )
        assert Stay.objects.filter(name="Hotel Roma", author=user).exists()

    def test_accept_empty_name_creates_nothing(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        response = self._post(user, trip, "experience", {"name": ""})
        self.response_200(response)
        assert not Event.objects.filter(trip=trip).exists()

    def test_accept_invalid_coordinates_ignored(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
            self._post(
                user, trip, "experience", {"name": "X", "lat": "abc", "lng": "abc"}
            )
        event = Event.objects.get(trip=trip, name="X")
        assert event.latitude is None

    def test_accept_without_coordinates(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
            self._post(user, trip, "experience", {"name": "NoCoords"})
        event = Event.objects.get(trip=trip, name="NoCoords")
        assert event.latitude is None

    def test_accept_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        response = self._post(other, trip, "experience", {"name": "X"})
        self.response_404(response)

    def test_accept_requires_login(self):
        trip = TripFactory()
        response = self.post("suggestions:accept-experience", pk=trip.pk)
        self.response_302(response)
