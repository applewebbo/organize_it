import json
from datetime import date
from unittest.mock import patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.schemas import ItineraryStop
from suggestions.services import GroundedDay, GroundedStop
from tests.suggestions.factories import AICredentialsFactory
from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import Event

pytestmark = pytest.mark.django_db


def _grounded_stop(kind, name, duration=90):
    return GroundedStop(
        stop=ItineraryStop(
            kind=kind,
            name=name,
            description="nice",
            estimated_duration_minutes=duration,
        ),
        address="Via Roma 1, Roma",
        city="Roma",
        latitude=41.9,
        longitude=12.5,
        place_id=f"place_{name}",
    )


def _grounded_day(day_date, destination, *stops):
    return GroundedDay(date=day_date, destination=destination, stops=list(stops))


def _stop_card(name, kind="experience"):
    return {
        "kind": kind,
        "name": name,
        "description": "",
        "icon": "ph-map-pin",
        "icon_color": "text-green-500",
        "address": "Via Roma 1",
        "city": "Roma",
        "lat": 41.9,
        "lng": 12.5,
        "place_id": f"place_{name}",
        "duration_minutes": 90,
        "existing_event_id": None,
    }


def _draft(author):
    return TripFactory(
        author=author,
        destination="Roma",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        wizard_completed=False,
        wizard_step=2,
    )


class TestWizardAIGenerate(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        response = self.post("trips:wizard-ai-generate", pk=trip.pk)
        self.response_302(response)

    def test_get_not_allowed(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            response = self.get("trips:wizard-ai-generate", pk=trip.pk)
        assert response.status_code == 405

    def test_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        trip = _draft(user)
        with self.login(user):
            response = self.post("trips:wizard-ai-generate", pk=trip.pk)
        assert response.status_code == 403

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        AICredentialsFactory(user=owner)
        other = self.make_user("other@example.com")
        AICredentialsFactory(user=other)
        trip = _draft(owner)
        with self.login(other):
            response = self.post("trips:wizard-ai-generate", pk=trip.pk)
        self.response_404(response)

    @patch("trips.views.wizard.generate_trip_itinerary")
    def test_renders_days_including_unmatched_date(self, mock_generate):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        first = trip.days.order_by("number").first()
        mock_generate.return_value = [
            _grounded_day(first.date, "Roma", _grounded_stop("experience", "Forum")),
            # A date outside the trip: the card renders without a day number.
            _grounded_day(date(2099, 1, 1), "Nowhere"),
        ]
        with self.login(user):
            response = self.post("trips:wizard-ai-generate", pk=trip.pk)
        self.response_200(response)
        content = response.content.decode()
        assert "Forum" in content
        assert "Day 1" in content

    @patch("trips.views.wizard.generate_trip_itinerary")
    def test_config_error_shows_settings_link(self, mock_generate):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        mock_generate.side_effect = AISuggestionError(
            "no key", kind=AISuggestionError.CONFIG
        )
        with self.login(user):
            response = self.post("trips:wizard-ai-generate", pk=trip.pk)
        assert "/accounts/profile/" in response.content.decode()

    @patch("trips.views.wizard.generate_trip_itinerary")
    def test_no_days_renders_empty_state(self, mock_generate):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        mock_generate.return_value = []
        with self.login(user):
            response = self.post("trips:wizard-ai-generate", pk=trip.pk)
        assert "No itinerary generated" in response.content.decode()

    @patch("trips.views.wizard.generate_trip_itinerary")
    def test_forwards_notes_and_refresh(self, mock_generate):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        mock_generate.return_value = []
        with self.login(user):
            self.post(
                "trips:wizard-ai-generate",
                pk=trip.pk,
                data={"notes": "with kids", "refresh": "1"},
            )
        assert mock_generate.call_args.args[2] == {"notes": "with kids"}
        assert mock_generate.call_args.args[4] is True


class TestWizardAIConfirm(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        response = self.post("trips:wizard-ai-confirm", pk=trip.pk)
        self.response_302(response)

    def test_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        trip = _draft(user)
        with self.login(user):
            response = self.post("trips:wizard-ai-confirm", pk=trip.pk)
        assert response.status_code == 403

    def test_applies_selected_days_and_advances_step(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        day = trip.days.order_by("number").first()
        payload = [{"date": day.date.isoformat(), "stops": [_stop_card("Forum")]}]
        with self.login(user):
            response = self.post(
                "trips:wizard-ai-confirm",
                pk=trip.pk,
                data={"days": json.dumps(payload)},
            )
        self.response_200(response)
        assert "Itinerary added" in response.content.decode()
        assert Event.objects.filter(trip=trip, day=day, name="Forum").exists()
        trip.refresh_from_db()
        assert trip.wizard_step == 3

    def test_ignores_unknown_date_and_empty_stops(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        payload = [
            {"date": "2099-01-01", "stops": [_stop_card("Ghost")]},
            {"date": trip.days.first().date.isoformat(), "stops": []},
        ]
        with self.login(user):
            self.post(
                "trips:wizard-ai-confirm",
                pk=trip.pk,
                data={"days": json.dumps(payload)},
            )
        assert not Event.objects.filter(trip=trip).exists()

    def test_invalid_json_advances_without_events(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        trip = _draft(user)
        with self.login(user):
            self.post("trips:wizard-ai-confirm", pk=trip.pk, data={"days": "not json"})
        assert not Event.objects.filter(trip=trip).exists()
        trip.refresh_from_db()
        assert trip.wizard_step == 3
