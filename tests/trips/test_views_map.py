from unittest.mock import MagicMock, patch

import pytest

from tests.test import TestCase
from tests.trips.factories import (
    ExperienceFactory,
    TripFactory,
)
from trips.models import Event, Stay
from trips.services import GooglePlacesError, PlaceResult

pytestmark = pytest.mark.django_db

# Geocoder mock: return no coordinates (avoids real HTTP calls)
MOCK_GEO = MagicMock()
MOCK_GEO.latlng = None

MOCK_PLACES = [
    PlaceResult(
        place_id="ChIJ_test_001",
        name="Museo Egizio",
        address="Via Accademia delle Scienze 6, Torino",
        lat=45.0687,
        lng=7.6847,
    ),
    PlaceResult(
        place_id="ChIJ_test_002",
        name="Ristorante Al Centro",
        address="Via Roma 1, Torino",
        lat=45.0703,
        lng=7.6869,
    ),
]


class TripMapViewTest(TestCase):
    def test_get_map_page_owner(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        self.response_200(response)
        assert response.context["trip"] == trip

    def test_get_map_page_unauthenticated(self):
        trip = TripFactory()
        response = self.get("trips:trip-map", pk=trip.pk)
        self.response_302(response)

    def test_get_map_page_other_user_forbidden(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("trips:trip-map", pk=trip.pk)
        self.response_404(response)

    def test_map_page_shows_events(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
            ExperienceFactory(trip=trip, day=day, latitude=45.0, longitude=7.0)
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        self.response_200(response)
        assert len(response.context["days_with_events"]) > 0

    def test_map_page_shows_unassigned_events(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        # Create unassigned event directly to avoid factory day-resolution issues
        with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
            Event.objects.create(
                trip=trip,
                day=None,
                name="Piazza Castello",
                address="Piazza Castello, Torino",
                latitude=45.0703,
                longitude=7.6869,
                category=Event.Category.EXPERIENCE,
            )
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        self.response_200(response)
        assert response.context["unassigned_events"].count() == 1


class MapSearchViewTest(TestCase):
    def test_search_returns_results(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = MOCK_PLACES
                response = self.post(
                    "trips:map-search",
                    pk=trip.pk,
                    data={"query": "museo torino"},
                )
        self.response_200(response)
        assert response.context["results"] == MOCK_PLACES
        assert response.context["query"] == "museo torino"

    def test_search_empty_query_returns_no_results(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:map-search",
                pk=trip.pk,
                data={"query": ""},
            )
        self.response_200(response)
        assert response.context["results"] == []

    def test_search_api_error_returns_error_context(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.side_effect = GooglePlacesError(
                    "API error"
                )
                response = self.post(
                    "trips:map-search",
                    pk=trip.pk,
                    data={"query": "museo"},
                )
        self.response_200(response)
        assert response.context["error"] is not None

    def test_search_forbidden_for_other_user(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.post(
                "trips:map-search",
                pk=trip.pk,
                data={"query": "museo"},
            )
        self.response_404(response)

    def test_search_requires_post(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:map-search", pk=trip.pk)
        self.response_405(response)


class MapAddExperienceViewTest(TestCase):
    def test_add_experience_creates_event(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        # Coords provided by Google → geocoder should NOT be called (coords not missing)
        with self.login(user):
            response = self.post(
                "trips:map-add-experience",
                pk=trip.pk,
                data={
                    "google_place_id": "ChIJ_test_001",
                    "name": "Museo Egizio",
                    "address": "Via Accademia delle Scienze 6, Torino",
                    "lat": "45.0687",
                    "lng": "7.6847",
                },
            )
        self.response_200(response)
        event = Event.objects.get(trip=trip, name="Museo Egizio")
        assert event.category == Event.Category.EXPERIENCE
        assert event.place_id == "ChIJ_test_001"
        assert event.latitude == 45.0687
        assert event.longitude == 7.6847
        assert event.day is None

    def test_add_experience_invalid_coords_are_skipped(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
                self.post(
                    "trips:map-add-experience",
                    pk=trip.pk,
                    data={
                        "google_place_id": "ChIJ_test_001",
                        "name": "Posto",
                        "address": "Via Roma",
                        "lat": "not-a-number",
                        "lng": "also-not",
                    },
                )
        event = Event.objects.get(trip=trip, name="Posto")
        assert event.latitude is None
        assert event.longitude is None

    def test_add_experience_empty_name_creates_nothing(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:map-add-experience",
                pk=trip.pk,
                data={
                    "google_place_id": "",
                    "name": "",
                    "address": "",
                    "lat": "",
                    "lng": "",
                },
            )
        self.response_200(response)
        assert Event.objects.filter(trip=trip).count() == 0

    def test_add_experience_forbidden_for_other_user(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.post(
                "trips:map-add-experience",
                pk=trip.pk,
                data={
                    "name": "Test",
                    "address": "",
                    "lat": "",
                    "lng": "",
                    "google_place_id": "",
                },
            )
        self.response_404(response)
        assert Event.objects.filter(trip=trip).count() == 0


class MapAddMealViewTest(TestCase):
    def test_add_meal_creates_meal_event(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:map-add-meal",
                pk=trip.pk,
                data={
                    "google_place_id": "ChIJ_test_002",
                    "name": "Ristorante Da Luigi",
                    "address": "Via Roma 1",
                    "lat": "45.07",
                    "lng": "7.68",
                },
            )
        self.response_200(response)
        event = Event.objects.get(trip=trip, name="Ristorante Da Luigi")
        assert event.category == Event.Category.MEAL

    def test_add_meal_empty_name_creates_nothing(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:map-add-meal",
                pk=trip.pk,
                data={
                    "google_place_id": "",
                    "name": "",
                    "address": "",
                    "lat": "",
                    "lng": "",
                },
            )
        self.response_200(response)
        assert Event.objects.filter(trip=trip).count() == 0


class MapAddStayViewTest(TestCase):
    def test_add_stay_creates_stay(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:map-add-stay",
                pk=trip.pk,
                data={
                    "google_place_id": "ChIJ_test_003",
                    "name": "Hotel Principi di Piemonte",
                    "address": "Via Gobetti 15, Torino",
                    "lat": "45.0703",
                    "lng": "7.6869",
                },
            )
        self.response_200(response)
        stay = Stay.objects.get(name="Hotel Principi di Piemonte")
        assert stay.place_id == "ChIJ_test_003"
        assert stay.latitude == 45.0703
        assert stay.author == user

    def test_add_stay_invalid_coords_are_skipped(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
                self.post(
                    "trips:map-add-stay",
                    pk=trip.pk,
                    data={
                        "google_place_id": "ChIJ_test_003",
                        "name": "Hotel X",
                        "address": "Via Roma",
                        "lat": "bad",
                        "lng": "bad",
                    },
                )
        stay = Stay.objects.get(name="Hotel X")
        assert stay.latitude is None
        assert stay.longitude is None

    def test_add_stay_without_lat_lng(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
                self.post(
                    "trips:map-add-stay",
                    pk=trip.pk,
                    data={
                        "google_place_id": "ChIJ_test_003",
                        "name": "Hotel Senza Coordinate",
                        "address": "Via Roma 1",
                        "lat": "",
                        "lng": "",
                    },
                )
        stay = Stay.objects.get(name="Hotel Senza Coordinate")
        assert stay.latitude is None
        assert stay.longitude is None

    def test_add_stay_empty_name_creates_nothing(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:map-add-stay",
                pk=trip.pk,
                data={
                    "google_place_id": "",
                    "name": "",
                    "address": "",
                    "lat": "",
                    "lng": "",
                },
            )
        self.response_200(response)
        assert Stay.objects.count() == 0

    def test_add_stay_forbidden_for_other_user(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.post(
                "trips:map-add-stay",
                pk=trip.pk,
                data={
                    "name": "Hotel X",
                    "address": "",
                    "lat": "",
                    "lng": "",
                    "google_place_id": "",
                },
            )
        self.response_404(response)
        assert Stay.objects.count() == 0


class BuildMapJsonTest(TestCase):
    """Tests for _build_map_json branches: stay/event/unassigned with coordinates."""

    def test_map_json_includes_stay_and_events_with_coords(self):
        """Covers _build_map_json branches for stay, event with lat/lng."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        # Event with coords — covers line 2959 branch
        Event.objects.create(
            trip=trip,
            day=day,
            name="Museo Egizio",
            address="Via Accademia 6, Torino",
            latitude=45.0687,
            longitude=7.6847,
            category=Event.Category.EXPERIENCE,
        )
        # Meal event with coords — covers meal kind branch
        Event.objects.create(
            trip=trip,
            day=day,
            name="Ristorante Da Luigi",
            address="Via Roma 1, Torino",
            latitude=45.0703,
            longitude=7.6869,
            category=Event.Category.MEAL,
        )
        # Stay with coords — covers line 2946 branch
        stay = Stay.objects.create(
            name="Hotel Torino",
            address="Via Po 1, Torino",
            latitude=45.07,
            longitude=7.68,
        )
        stay.days.add(day)

        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)

        self.response_200(response)
        import json

        map_items = json.loads(response.context["map_items_json"])
        kinds = {item["kind"] for item in map_items}
        assert "stay" in kinds
        assert "experience" in kinds
        assert "meal" in kinds

    def test_map_json_includes_unassigned_events_with_coords(self):
        """Covers _build_map_json branch for unassigned events with lat/lng (line 2972)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        Event.objects.create(
            trip=trip,
            day=None,
            name="Piazza Castello",
            address="Piazza Castello, Torino",
            latitude=45.0703,
            longitude=7.6869,
            category=Event.Category.EXPERIENCE,
        )

        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)

        self.response_200(response)
        import json

        map_items = json.loads(response.context["map_items_json"])
        unassigned = [i for i in map_items if i["day_index"] == 0]
        assert len(unassigned) == 1
        assert unassigned[0]["name"] == "Piazza Castello"

    def test_map_json_skips_events_without_coords(self):
        """Covers false branch of 'if event.latitude and event.longitude' (lines 2959, 2972)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
            # Assigned event without coords
            Event.objects.create(
                trip=trip,
                day=day,
                name="No Coords Assigned",
                address="Somewhere",
                latitude=None,
                longitude=None,
                category=Event.Category.EXPERIENCE,
            )
            # Unassigned event without coords
            Event.objects.create(
                trip=trip,
                day=None,
                name="No Coords Unassigned",
                address="Somewhere",
                latitude=None,
                longitude=None,
                category=Event.Category.EXPERIENCE,
            )

        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)

        self.response_200(response)
        import json

        map_items = json.loads(response.context["map_items_json"])
        names = [i["name"] for i in map_items]
        assert "No Coords Assigned" not in names
        assert "No Coords Unassigned" not in names


class TripLocationBiasTest(TestCase):
    """Tests for _trip_location_bias branches via map_search."""

    def test_search_uses_coords_from_existing_events(self):
        """Covers _trip_location_bias when all_coords is non-empty (line 3041→3042)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        Event.objects.create(
            trip=trip,
            day=day,
            name="Test Event",
            address="Via Roma 1",
            latitude=45.07,
            longitude=7.68,
            category=Event.Category.EXPERIENCE,
        )

        with self.login(user):
            with patch("trips.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None
        lat, lng, radius = call_kwargs["location_bias"]
        assert lat == 45.07
        assert lng == 7.68

    def test_search_falls_back_to_geocoding_destination(self):
        """Covers _trip_location_bias fallback to geocoder (lines 3048, 3050)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)  # no events with coords

        mock_geo = MagicMock()
        mock_geo.latlng = [45.07, 7.68]

        with self.login(user):
            with patch("trips.views.GooglePlacesClient") as MockClient:
                with patch("trips.views.geocoder.mapbox", return_value=mock_geo):
                    MockClient.return_value.search_text.return_value = []
                    self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None
        assert call_kwargs["location_bias"][2] == 50_000

    def test_search_geocoder_no_latlng_returns_none_bias(self):
        """Covers _trip_location_bias false branch of 'if g.latlng' (line 3050)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)  # no events with coords

        mock_geo = MagicMock()
        mock_geo.latlng = None  # geocoder finds nothing

        with self.login(user):
            with patch("trips.views.GooglePlacesClient") as MockClient:
                with patch("trips.views.geocoder.mapbox", return_value=mock_geo):
                    MockClient.return_value.search_text.return_value = []
                    self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is None

    def test_search_no_destination_returns_none_bias(self):
        """Covers _trip_location_bias false branch of 'if trip.destination' (line 3048)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user, destination="")  # no destination, no events

        with self.login(user):
            with patch("trips.views.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is None


class MapAddExperienceLatLngTest(TestCase):
    """Covers line 3104: 'if lat and lng' false branch (no coords provided)."""

    def test_add_experience_without_lat_lng(self):
        """When lat/lng are empty strings, coords are not set (line 3104 false branch)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
                response = self.post(
                    "trips:map-add-experience",
                    pk=trip.pk,
                    data={
                        "google_place_id": "ChIJ_test_001",
                        "name": "Luogo Senza Coordinate",
                        "address": "Via Roma 1",
                        "lat": "",
                        "lng": "",
                    },
                )
        self.response_200(response)
        event = Event.objects.get(trip=trip, name="Luogo Senza Coordinate")
        assert event.latitude is None
        assert event.longitude is None

    def test_add_meal_without_lat_lng(self):
        """When lat/lng are empty strings for meal, coords are not set."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.models.geocoder.mapbox", return_value=MOCK_GEO):
                response = self.post(
                    "trips:map-add-meal",
                    pk=trip.pk,
                    data={
                        "google_place_id": "ChIJ_test_002",
                        "name": "Ristorante Senza Coordinate",
                        "address": "Via Roma 1",
                        "lat": "",
                        "lng": "",
                    },
                )
        self.response_200(response)
        event = Event.objects.get(trip=trip, name="Ristorante Senza Coordinate")
        assert event.latitude is None
        assert event.longitude is None
