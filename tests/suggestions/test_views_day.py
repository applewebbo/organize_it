import json
from datetime import timedelta
from unittest.mock import patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.schemas import ItineraryStop
from suggestions.services import GroundedStop
from tests.test import TestCase
from tests.trips.factories import ExperienceFactory, MealFactory, TripFactory
from trips.models import Event, Experience, Meal

pytestmark = pytest.mark.django_db


def _grounded(kind, name, duration=None, existing_event_id=None):
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
        existing_event_id=existing_event_id,
    )


class TestPlanDayModal(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        response = self.get(
            "suggestions:plan-day-modal", pk=trip.pk, day_id=trip.days.first().pk
        )
        self.response_302(response)

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get(
                "suggestions:plan-day-modal", pk=trip.pk, day_id=trip.days.first().pk
            )
        self.response_404(response)

    def test_day_not_in_trip_404(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        other_trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "suggestions:plan-day-modal",
                pk=trip.pk,
                day_id=other_trip.days.first().pk,
            )
        self.response_404(response)

    def test_renders_without_events(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "suggestions:plan-day-modal", pk=trip.pk, day_id=trip.days.first().pk
            )
        self.response_200(response)
        assert response.context["has_events"] is False
        assert "This day already has events" not in response.content.decode()

    def test_renders_strategy_choices_with_events(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, name="Colosseo")
        with self.login(user):
            response = self.get("suggestions:plan-day-modal", pk=trip.pk, day_id=day.pk)
        self.response_200(response)
        assert response.context["has_events"] is True
        assert "This day already has events" in response.content.decode()


class TestGenerateDayView(TestCase):
    def test_requires_login(self):
        trip = TripFactory()
        response = self.post(
            "suggestions:generate-day", pk=trip.pk, day_id=trip.days.first().pk
        )
        self.response_302(response)

    def test_get_not_allowed(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "suggestions:generate-day", pk=trip.pk, day_id=trip.days.first().pk
            )
        assert response.status_code == 405

    @patch("suggestions.views.generate_day_itinerary")
    def test_renders_stops(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = [
            _grounded("experience", "Forum", duration=120),
            _grounded("meal", "Trattoria", duration=60),
        ]
        with self.login(user):
            response = self.post(
                "suggestions:generate-day",
                pk=trip.pk,
                day_id=trip.days.first().pk,
                data={"notes": "with kids"},
            )
        self.response_200(response)
        content = response.content.decode()
        assert "Forum" in content
        assert "Trattoria" in content
        # notes forwarded as override
        assert mock_generate.call_args.args[3] == "add"
        assert mock_generate.call_args.args[4] == {"notes": "with kids"}

    @patch("suggestions.views.generate_day_itinerary")
    def test_invalid_strategy_defaults_to_add(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = []
        with self.login(user):
            self.post(
                "suggestions:generate-day",
                pk=trip.pk,
                day_id=trip.days.first().pk,
                data={"strategy": "bogus"},
            )
        assert mock_generate.call_args.args[3] == "add"

    @patch("suggestions.views.generate_day_itinerary")
    def test_forwards_strategy_and_refresh(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = []
        with self.login(user):
            self.post(
                "suggestions:generate-day",
                pk=trip.pk,
                day_id=trip.days.first().pk,
                data={"strategy": "delete", "refresh": "1"},
            )
        assert mock_generate.call_args.args[3] == "delete"
        assert mock_generate.call_args.args[6] is True

    @patch("suggestions.views.generate_day_itinerary")
    def test_config_error_shows_settings_link(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.side_effect = AISuggestionError(
            "no key", kind=AISuggestionError.CONFIG
        )
        with self.login(user):
            response = self.post(
                "suggestions:generate-day", pk=trip.pk, day_id=trip.days.first().pk
            )
        content = response.content.decode()
        assert "/accounts/profile/" in content

    @patch("suggestions.views.generate_day_itinerary")
    def test_no_itinerary(self, mock_generate):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_generate.return_value = []
        with self.login(user):
            response = self.post(
                "suggestions:generate-day", pk=trip.pk, day_id=trip.days.first().pk
            )
        assert "No itinerary generated" in response.content.decode()


class TestAcceptDayView(TestCase):
    def _accept(self, user, trip, day, strategy, stops):
        with self.login(user):
            return self.post(
                "suggestions:accept-day",
                pk=trip.pk,
                day_id=day.pk,
                data={"strategy": strategy, "stops": json.dumps(stops)},
            )

    def test_requires_login(self):
        trip = TripFactory()
        response = self.post(
            "suggestions:accept-day", pk=trip.pk, day_id=trip.days.first().pk
        )
        self.response_302(response)

    def test_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        response = self._accept(other, trip, trip.days.first(), "add", [])
        self.response_404(response)

    def test_add_creates_new_events_in_order(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stops = [
            {
                "kind": "experience",
                "name": "Forum",
                "address": "Via A",
                "lat": 41.9,
                "lng": 12.5,
                "duration_minutes": 120,
            },
            {"kind": "meal", "name": "Trattoria"},
        ]
        response = self._accept(user, trip, day, "add", stops)
        self.response_200(response)
        assert response["HX-Trigger"] == f"dayModified{day.pk}, unpairedModified"
        forum = Event.objects.get(trip=trip, name="Forum")
        assert forum.day == day
        assert forum.order == 0
        assert forum.category == Event.Category.EXPERIENCE
        assert forum.estimated_duration == timedelta(minutes=120)
        assert Experience.objects.filter(pk=forum.pk).exists()
        trattoria = Event.objects.get(trip=trip, name="Trattoria")
        assert trattoria.order == 1
        assert Meal.objects.filter(pk=trattoria.pk).exists()

    def test_add_reorders_existing_and_appends_deselected(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        existing = ExperienceFactory(trip=trip, day=day, name="Colosseo", order=0)
        deselected = MealFactory(trip=trip, day=day, name="Old Diner", order=1)
        # itinerary places a new stop before the existing (reused) event; the
        # deselected existing event is not part of the submitted stops.
        stops = [
            {"kind": "meal", "name": "New Bistro"},
            {
                "kind": "experience",
                "name": "Colosseo",
                "existing_event_id": existing.pk,
            },
        ]
        self._accept(user, trip, day, "add", stops)
        existing.refresh_from_db()
        deselected.refresh_from_db()
        new = Event.objects.get(trip=trip, name="New Bistro")
        assert new.order == 0
        assert existing.order == 1
        assert existing.day == day
        # deselected existing event stays on the day, appended after the sequence
        assert deselected.day == day
        assert deselected.order == 2

    def test_unpair_detaches_existing_and_creates_new(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        existing = ExperienceFactory(trip=trip, day=day, name="Colosseo")
        self._accept(
            user, trip, day, "unpair", [{"kind": "experience", "name": "Forum"}]
        )
        existing.refresh_from_db()
        assert existing.day is None
        forum = Event.objects.get(trip=trip, name="Forum")
        assert forum.day == day
        assert forum.order == 0

    def test_delete_removes_existing_and_creates_new(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, name="Colosseo")
        self._accept(
            user, trip, day, "delete", [{"kind": "experience", "name": "Forum"}]
        )
        assert not Event.objects.filter(trip=trip, name="Colosseo").exists()
        assert Event.objects.filter(trip=trip, name="Forum", day=day).exists()

    def test_invalid_json_applies_nothing(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with self.login(user):
            response = self.post(
                "suggestions:accept-day",
                pk=trip.pk,
                day_id=day.pk,
                data={"strategy": "add", "stops": "not-json"},
            )
        self.response_200(response)
        assert not Event.objects.filter(trip=trip).exists()

    def test_invalid_strategy_defaults_to_add(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        existing = ExperienceFactory(trip=trip, day=day, name="Colosseo")
        self._accept(
            user, trip, day, "bogus", [{"kind": "experience", "name": "Forum"}]
        )
        # add behaviour: existing kept on the day
        existing.refresh_from_db()
        assert existing.day == day

    def test_empty_name_and_stay_kind_skipped(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stops = [
            {"kind": "experience", "name": ""},
            {"kind": "stay", "name": "Hotel"},
            {"kind": "experience", "name": "Forum"},
        ]
        self._accept(user, trip, day, "add", stops)
        names = set(Event.objects.filter(trip=trip).values_list("name", flat=True))
        assert names == {"Forum"}

    def test_invalid_coordinates_ignored(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stops = [{"kind": "experience", "name": "Forum", "lat": "x", "lng": "y"}]
        with patch("trips.models.geocoder.mapbox") as geo:
            geo.return_value.latlng = None
            self._accept(user, trip, day, "add", stops)
        forum = Event.objects.get(trip=trip, name="Forum")
        assert forum.latitude is None
