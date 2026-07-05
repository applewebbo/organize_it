import json
from unittest.mock import MagicMock, patch

import pytest

from tests.test import TestCase
from tests.trips.factories import (
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.models import Event, Experience, Meal, Stay
from trips.services import GooglePlacesError, PlaceFullDetails, PlaceResult

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


class TestTripMapView(TestCase):
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


class TestMapAITabGating(TestCase):
    def test_ai_tab_hidden_when_disabled(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        assert "AI suggestions" not in response.content.decode()

    def test_ai_tab_shown_when_enabled(self):
        user = self.make_user("owner@example.com")
        user.profile.ai_suggestions_enabled = True
        user.profile.save()
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        assert "AI suggestions" in response.content.decode()


class TestMapStageCoords(TestCase):
    def test_main_stage_coords_from_trip(self):
        user = self.make_user("owner@example.com")
        geo = MagicMock()
        geo.latlng = [45.07, 7.68]
        with patch("trips.models.geocoder.mapbox", return_value=geo):
            trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        coords = json.loads(response.context["stage_coords_json"])
        assert coords[trip.destination] == [45.07, 7.68]

    def test_custom_stage_coords_are_day_average(self):
        user = self.make_user("owner@example.com")
        geo = MagicMock()
        geo.latlng = None
        with patch("trips.models.geocoder.mapbox", return_value=geo):
            trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        for day, (lat, lng) in zip(
            days[-2:], [(41.9, 12.5), (41.8, 12.4)], strict=False
        ):
            day.destination = "Roma"
            day.destination_latitude = lat
            day.destination_longitude = lng
            day.save()
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        coords = json.loads(response.context["stage_coords_json"])
        assert coords["Roma"] == [pytest.approx(41.85), pytest.approx(12.45)]

    def test_custom_stage_falls_back_to_event_coords(self):
        user = self.make_user("owner@example.com")
        geo = MagicMock()
        geo.latlng = None
        with patch("trips.models.geocoder.mapbox", return_value=geo):
            trip = TripFactory(author=user)
        day = trip.days.order_by("number").last()
        day.destination = "Roma"
        day.save()
        # Stage day has no destination coords: the event's coords locate it.
        with patch("trips.models.geocoder.mapbox", return_value=geo):
            Event.objects.create(
                trip=trip,
                day=day,
                name="Colosseo",
                latitude=41.89,
                longitude=12.49,
                category=Event.Category.EXPERIENCE,
            )
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        coords = json.loads(response.context["stage_coords_json"])
        assert coords["Roma"] == [pytest.approx(41.89), pytest.approx(12.49)]

    def test_stage_without_coords_is_omitted(self):
        user = self.make_user("owner@example.com")
        geo = MagicMock()
        geo.latlng = None
        with patch("trips.models.geocoder.mapbox", return_value=geo):
            trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        last = days[-1]
        last.destination = "Napoli"
        last.save()
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        coords = json.loads(response.context["stage_coords_json"])
        assert "Napoli" not in coords
        assert trip.destination not in coords


class TestMapSearchView(TestCase):
    def test_search_returns_results(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
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
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
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


class TestMapAddExperienceView(TestCase):
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
        # STI child row exists so the event-detail modal works (#368)
        assert Experience.objects.filter(pk=event.pk).exists()
        with self.login(user):
            detail = self.get("trips:event-detail", pk=event.pk)
        self.response_200(detail)

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


class TestMapAddMealView(TestCase):
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
        # STI child row exists so the event-detail modal works (#368)
        assert Meal.objects.filter(pk=event.pk).exists()
        with self.login(user):
            detail = self.get("trips:event-detail", pk=event.pk)
        self.response_200(detail)

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


class TestMapAddStayView(TestCase):
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


class TestBuildMapJson(TestCase):
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
        # Main-stage days (blank destination) are tagged with the trip destination
        assert all(item["stage"] == trip.destination for item in map_items)

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
        assert unassigned[0]["stage"] is None

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


class TestTripLocationBias(TestCase):
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
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None
        lat, lng, radius = call_kwargs["location_bias"]
        assert lat == 45.07
        assert lng == 7.68

    def test_location_bias_radius_capped_at_50km(self):
        """radius must never exceed 50,000 m (Google Places API limit)."""
        user = self.make_user("bias_cap@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        # Two events ~900 km apart — without cap radius would far exceed 50 km
        for lat, lng in [(41.9, 12.5), (48.85, 2.35)]:
            Event.objects.create(
                trip=trip,
                day=day,
                name="Event",
                address="addr",
                latitude=lat,
                longitude=lng,
                category=Event.Category.EXPERIENCE,
            )

        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        _, _, radius = MockClient.return_value.search_text.call_args.kwargs[
            "location_bias"
        ]
        assert radius <= 50_000

    def test_search_falls_back_to_geocoding_destination(self):
        """Covers _trip_location_bias fallback to geocoder (lines 3048, 3050)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)  # no events with coords

        mock_geo = MagicMock()
        mock_geo.latlng = [45.07, 7.68]

        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch(
                    "trips.views.maps.geocoder.mapbox", return_value=mock_geo
                ) as mock_mapbox:
                    MockClient.return_value.search_text.return_value = []
                    self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None
        assert call_kwargs["location_bias"][2] == 50_000
        # place-level lookup so an ambiguous destination cannot match a country
        assert mock_mapbox.call_args.kwargs["types"] == "place"

    def test_search_geocoder_no_latlng_returns_none_bias(self):
        """Covers _trip_location_bias false branch of 'if g.latlng' (line 3050)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)  # no events with coords

        mock_geo = MagicMock()
        mock_geo.latlng = None  # geocoder finds nothing

        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch("trips.views.maps.geocoder.mapbox", return_value=mock_geo):
                    MockClient.return_value.search_text.return_value = []
                    self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is None

    def test_search_no_destination_returns_none_bias(self):
        """Covers _trip_location_bias false branch of 'if trip.destination' (line 3048)."""
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user, destination="")  # no destination, no events

        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post("trips:map-search", pk=trip.pk, data={"query": "museo"})

        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is None


class TestMapAddExperienceLatLng(TestCase):
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


class TestTripEventsMapFragment(TestCase):
    def test_owner_gets_map_fragment(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-events-map", pk=trip.pk)
        self.response_200(response)
        assert response.context["trip"] == trip

    def test_unauthorized_user_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("trips:trip-events-map", pk=trip.pk)
        self.response_404(response)

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        response = self.get("trips:trip-events-map", pk=trip.pk)
        self.response_302(response)


class TestTripEventsListFragment(TestCase):
    def test_owner_gets_list_fragment(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-events-list", pk=trip.pk)
        self.response_200(response)
        assert response.context["trip"] == trip

    def test_unauthorized_user_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("trips:trip-events-list", pk=trip.pk)
        self.response_404(response)

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        response = self.get("trips:trip-events-list", pk=trip.pk)
        self.response_302(response)


class TestSelectDayForEvent(TestCase):
    def test_owner_gets_day_selector_experience(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "trips:select-day-for-event", pk=trip.pk, category="experience"
            )
        self.response_200(response)
        assert response.context["category"] == "experience"

    def test_owner_gets_day_selector_meal(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "trips:select-day-for-event", pk=trip.pk, category="meal"
            )
        self.response_200(response)
        assert response.context["category"] == "meal"

    def test_invalid_category_returns_404(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "trips:select-day-for-event", pk=trip.pk, category="invalid"
            )
        self.response_404(response)

    def test_non_editor_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get(
                "trips:select-day-for-event", pk=trip.pk, category="experience"
            )
        self.response_404(response)

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        response = self.get(
            "trips:select-day-for-event", pk=trip.pk, category="experience"
        )
        self.response_302(response)


MOCK_FULL_DETAILS = PlaceFullDetails(
    place_id="ChIJ_test_001",
    name="Museo Egizio",
    address="Via Accademia delle Scienze 6, 10123 Torino TO, Italia",
    city="Torino",
    lat=45.0687,
    lng=7.6847,
    website="https://museoegizio.it",
    phone_number="+39 011 561 7776",
    opening_hours={
        "monday": {"open": "09:00", "close": "18:30"},
        "tuesday": {"open": "09:00", "close": "18:30"},
    },
)

MOCK_FULL_DETAILS_NO_HOURS = PlaceFullDetails(
    place_id="ChIJ_test_002",
    name="Piazza Castello",
    address="Piazza Castello, Torino",
    city="Torino",
    lat=45.0712,
    lng=7.6858,
    website="",
    phone_number="",
    opening_hours=None,
)


class TestResolveMapsLinkView(TestCase):
    def test_invalid_url_returns_error(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.post(
                "trips:resolve-maps-link",
                data={"maps_link": "https://example.com/not-a-maps-link"},
            )
        self.response_200(response)
        assert response.context["error"] is True

    def test_full_google_maps_url_no_place_id_returns_error(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch(
                "trips.views.maps.GooglePlacesClient.search_text",
                return_value=[],
            ):
                response = self.post(
                    "trips:resolve-maps-link",
                    data={
                        "maps_link": "https://www.google.com/maps/place/Foo/@45.0,7.0,17z"
                    },
                )
        self.response_200(response)
        assert response.context["error"] is True

    def test_full_google_maps_url_success(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch(
                "trips.views.maps.GooglePlacesClient.search_text",
                return_value=[
                    PlaceResult(
                        place_id="ChIJtest789",
                        name="Foo",
                        address="Via Foo",
                        lat=45.0,
                        lng=7.0,
                    )
                ],
            ):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={
                            "maps_link": "https://www.google.com/maps/place/Foo/@45.0,7.0,17z"
                        },
                    )
        self.response_200(response)
        assert response.context["found"] is True

    def test_goo_gl_maps_url_success(self):
        user = self.make_user("user@example.com")
        mock_resp = MagicMock()
        mock_resp.url = "https://www.google.com/maps/place/Museo/@45.06,7.68,17z/data=!3m1!4b1!4m6!3m5!1s!1sChIJtest123!8m2!3d45!4d7"
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": "https://goo.gl/maps/abc123"},
                    )
        self.response_200(response)
        assert response.context["found"] is True

    def test_empty_url_returns_error(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.post(
                "trips:resolve-maps-link",
                data={"maps_link": ""},
            )
        self.response_200(response)
        assert response.context["error"] is True

    def test_redirect_failure_returns_error(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch(
                "trips.views.maps.requests.get", side_effect=Exception("timeout")
            ):
                response = self.post(
                    "trips:resolve-maps-link",
                    data={"maps_link": "https://maps.app.goo.gl/abc123"},
                )
        self.response_200(response)
        assert response.context["error"] is True

    def test_no_place_id_in_expanded_url_returns_error(self):
        user = self.make_user("user@example.com")
        mock_resp = MagicMock()
        mock_resp.url = "https://www.google.com/maps/place/No+Place+ID+Here"
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                response = self.post(
                    "trips:resolve-maps-link",
                    data={"maps_link": "https://maps.app.goo.gl/abc123"},
                )
        self.response_200(response)
        assert response.context["error"] is True

    def test_places_api_error_returns_error(self):
        user = self.make_user("user@example.com")
        mock_resp = MagicMock()
        mock_resp.url = "https://www.google.com/maps/place/Museo/@45.06,7.68,17z/data=!3m1!4b1!4m6!3m5!1s!1sChIJtest123!8m2!3d45!4d7"
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    side_effect=GooglePlacesError("API error"),
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": "https://maps.app.goo.gl/abc123"},
                    )
        self.response_200(response)
        assert response.context["error"] is True

    def test_success_returns_details_with_opening_hours(self):
        import json as _json

        user = self.make_user("user@example.com")
        mock_resp = MagicMock()
        mock_resp.url = "https://www.google.com/maps/place/Museo/@45.06,7.68,17z/data=!3m1!4b1!4m6!3m5!1s!1sChIJtest123!8m2!3d45!4d7"
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": "https://maps.app.goo.gl/abc123"},
                    )
        self.response_200(response)
        assert response.context["found"] is True
        data = _json.loads(response.context["place_data_json"])
        assert data["name"] == "Museo Egizio"
        assert data["opening_hours"] is not None

    def test_success_returns_details_without_opening_hours(self):
        import json as _json

        user = self.make_user("user@example.com")
        mock_resp = MagicMock()
        mock_resp.url = "https://www.google.com/maps/place/Piazza/@45.07,7.68,17z/data=!3m1!4b1!4m6!3m5!1s!1sChIJtest456!8m2!3d45!4d7"
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS_NO_HOURS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": "https://maps.app.goo.gl/def456"},
                    )
        self.response_200(response)
        assert response.context["found"] is True
        data = _json.loads(response.context["place_data_json"])
        assert data["opening_hours"] is None

    def test_consent_redirect_is_followed(self):
        """maps.py:593 — consent.google.com redirect extracts the real Maps URL."""
        import urllib.parse as _up

        real_maps_url = "https://www.google.com/maps/place/Museo/@45.06,7.68,17z/data=!3m1!4b1!4m6!3m5!1s!1sChIJtest123!8m2!3d45!4d7"
        consent_url = "https://consent.google.com/m?continue=" + _up.quote(
            real_maps_url
        )
        mock_resp = MagicMock()
        mock_resp.url = consent_url
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": "https://maps.app.goo.gl/abc123"},
                    )
        self.response_200(response)
        assert response.context["found"] is True

    def test_consent_redirect_without_continue_param_returns_error(self):
        """maps.py:595 false — consent redirect has no 'continue' param → place_id not found."""
        mock_resp = MagicMock()
        mock_resp.url = "https://consent.google.com/m?hl=it"
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                response = self.post(
                    "trips:resolve-maps-link",
                    data={"maps_link": "https://maps.app.goo.gl/abc123"},
                )
        self.response_200(response)
        assert response.context["error"] is True

    def test_fallback_search_api_error_returns_error(self):
        """maps.py:638/639 — Places API error during fallback text search."""
        url = "https://www.google.com/maps/place/Foo/@45.0,7.0,17z"
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch(
                "trips.views.maps.GooglePlacesClient.search_text",
                side_effect=GooglePlacesError("API error"),
            ):
                response = self.post(
                    "trips:resolve-maps-link",
                    data={"maps_link": url},
                )
        self.response_200(response)
        assert response.context["error"] is True

    def test_fallback_uses_3d_4d_coords_as_bias(self):
        """maps.py:616 false, 632 — URL with !3d/!4d but no ChIJ place_id."""
        # URL has !3d/!4d coords but hex place_id (not ChIJ) → triggers fallback
        url = "https://www.google.com/maps/place/Colosseo/@41.89,12.49,17z/data=!4m5!3m4!1s0x12d5e4d8:0xbe9d!8m2!3d41.89!4d12.49"
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch(
                "trips.views.maps.GooglePlacesClient.search_text",
                return_value=[
                    PlaceResult(
                        place_id="ChIJtest999",
                        name="Colosseo",
                        address="Piazza del Colosseo",
                        lat=41.89,
                        lng=12.49,
                    )
                ],
            ) as mock_search:
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": url},
                    )
        self.response_200(response)
        assert response.context["found"] is True
        # location_bias should use !3d/!4d values
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["location_bias"] is not None

    def test_fallback_no_name_match_returns_error(self):
        """maps.py:627 false — URL without /place/ segment → name_match fails."""
        url = "https://www.google.com/maps/search/?q=foo"
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.post(
                "trips:resolve-maps-link",
                data={"maps_link": url},
            )
        self.response_200(response)
        assert response.context["error"] is True

    def test_get_not_allowed(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.get("trips:resolve-maps-link")
        self.response_405(response)

    def test_mobile_share_link_q_format_success(self):
        """maps.app.goo.gl?g_st=ic expands to ?q= format → fallback via Places text search."""
        mock_resp = MagicMock()
        mock_resp.url = "https://maps.google.com/maps?q=Museo+Egizio&ll=45.0687,7.6847"
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.search_text",
                    return_value=[
                        PlaceResult(
                            place_id="ChIJtest_mobile",
                            name="Museo Egizio",
                            address="Via Accademia delle Scienze 6, Torino",
                            lat=45.0687,
                            lng=7.6847,
                        )
                    ],
                ) as mock_search:
                    with patch(
                        "trips.views.maps.GooglePlacesClient.get_full_place_details",
                        return_value=MOCK_FULL_DETAILS,
                    ):
                        response = self.post(
                            "trips:resolve-maps-link",
                            data={
                                "maps_link": "https://maps.app.goo.gl/e6NRy6mLTXRvNKfW8?g_st=ic"
                            },
                        )
        self.response_200(response)
        assert response.context["found"] is True
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["location_bias"] is not None

    def test_mobile_share_link_q_format_no_ll_success(self):
        """?q= format without ll= param → text search without location bias."""
        mock_resp = MagicMock()
        mock_resp.url = "https://maps.google.com/maps?q=Museo+Egizio"
        user = self.make_user("user2@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.search_text",
                    return_value=[
                        PlaceResult(
                            place_id="ChIJtest_mobile2",
                            name="Museo Egizio",
                            address="Via Accademia delle Scienze 6, Torino",
                            lat=45.0687,
                            lng=7.6847,
                        )
                    ],
                ) as mock_search:
                    with patch(
                        "trips.views.maps.GooglePlacesClient.get_full_place_details",
                        return_value=MOCK_FULL_DETAILS,
                    ):
                        response = self.post(
                            "trips:resolve-maps-link",
                            data={"maps_link": "https://maps.app.goo.gl/abc?g_st=ic"},
                        )
        self.response_200(response)
        assert response.context["found"] is True
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["location_bias"] is None

    def test_mobile_share_link_q_format_empty_q_returns_error(self):
        """?q= format with empty q param → error."""
        mock_resp = MagicMock()
        mock_resp.url = "https://maps.google.com/maps?q="
        user = self.make_user("user3@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                response = self.post(
                    "trips:resolve-maps-link",
                    data={"maps_link": "https://maps.app.goo.gl/xyz?g_st=ic"},
                )
        self.response_200(response)
        assert response.context["error"] is True

    def test_mobile_share_link_q_format_invalid_ll_falls_back(self):
        """?q= format with malformed ll= values → no location bias, still searches."""
        mock_resp = MagicMock()
        mock_resp.url = "https://maps.google.com/maps?q=Museo+Egizio&ll=not,valid"
        user = self.make_user("user4@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.search_text",
                    return_value=[
                        PlaceResult(
                            place_id="ChIJtest_invalid_ll",
                            name="Museo Egizio",
                            address="Via Accademia delle Scienze 6, Torino",
                            lat=45.0687,
                            lng=7.6847,
                        )
                    ],
                ) as mock_search:
                    with patch(
                        "trips.views.maps.GooglePlacesClient.get_full_place_details",
                        return_value=MOCK_FULL_DETAILS,
                    ):
                        response = self.post(
                            "trips:resolve-maps-link",
                            data={"maps_link": "https://maps.app.goo.gl/abc?g_st=ic"},
                        )
        self.response_200(response)
        assert response.context["found"] is True
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["location_bias"] is None


class TestResolveMapsMismatch(TestCase):
    """Tests for soft place-type validation in resolve_maps_link (for #321)."""

    SHORT_URL = "https://maps.app.goo.gl/test123"
    EXPANDED_URL = (
        "https://www.google.com/maps/place/Test/@45.07,7.68,17z/data=!1sChIJtest321"
    )

    def _post_with_types(self, form_type, place_types):
        mock_resp = MagicMock()
        mock_resp.url = self.EXPANDED_URL
        details = PlaceFullDetails(
            place_id="ChIJtest321",
            name="Test Place",
            address="Via Test 1",
            city="Torino",
            lat=45.07,
            lng=7.68,
            types=place_types,
        )
        user = self.make_user(f"{form_type}@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=details,
                ):
                    return self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": self.SHORT_URL, "form_type": form_type},
                    )

    def test_stay_form_with_lodging_no_warning(self):
        response = self._post_with_types("stay", ["lodging", "hotel", "establishment"])
        assert response.context["found"] is True
        assert response.context.get("type_warning") is None

    def test_stay_form_with_non_lodging_shows_warning(self):
        response = self._post_with_types(
            "stay", ["restaurant", "food", "establishment"]
        )
        assert response.context["found"] is True
        assert response.context["type_warning"] == "stay_mismatch"

    def test_meal_form_with_restaurant_no_warning(self):
        response = self._post_with_types(
            "meal", ["restaurant", "food", "establishment"]
        )
        assert response.context["found"] is True
        assert response.context.get("type_warning") is None

    def test_meal_form_with_non_food_shows_warning(self):
        response = self._post_with_types("meal", ["lodging", "hotel", "establishment"])
        assert response.context["found"] is True
        assert response.context["type_warning"] == "meal_mismatch"

    def test_experience_form_with_museum_no_warning(self):
        response = self._post_with_types(
            "experience", ["tourist_attraction", "museum", "establishment"]
        )
        assert response.context["found"] is True
        assert response.context.get("type_warning") is None

    def test_experience_form_with_lodging_shows_warning(self):
        response = self._post_with_types(
            "experience", ["lodging", "hotel", "establishment"]
        )
        assert response.context["found"] is True
        assert response.context["type_warning"] == "experience_lodging"

    def test_experience_form_with_restaurant_shows_warning(self):
        response = self._post_with_types(
            "experience", ["restaurant", "food", "establishment"]
        )
        assert response.context["found"] is True
        assert response.context["type_warning"] == "experience_food"

    def test_no_form_type_no_warning(self):
        mock_resp = MagicMock()
        mock_resp.url = self.EXPANDED_URL
        user = self.make_user("noform@example.com")
        with self.login(user):
            with patch("trips.views.maps.requests.get", return_value=mock_resp):
                with patch(
                    "trips.views.maps.GooglePlacesClient.get_full_place_details",
                    return_value=MOCK_FULL_DETAILS,
                ):
                    response = self.post(
                        "trips:resolve-maps-link",
                        data={"maps_link": self.SHORT_URL},
                    )
        assert response.context["found"] is True
        assert response.context.get("type_warning") is None

    def test_meal_form_with_cafe_no_warning(self):
        response = self._post_with_types(
            "meal", ["cafe", "coffee_shop", "establishment"]
        )
        assert response.context["found"] is True
        assert response.context.get("type_warning") is None


class TestStaySaveSkipsGeocodingWhenCoordsProvided(TestCase):
    def test_save_with_coords_skips_mapbox(self):
        stay = StayFactory.build(
            latitude=45.0687,
            longitude=7.6847,
        )
        with patch("trips.models.geocoder.mapbox") as mock_geo:
            stay.save()
        mock_geo.assert_not_called()
        assert stay.latitude == 45.0687
        assert stay.longitude == 7.6847

    def test_save_without_coords_calls_mapbox(self):
        mock_geo = MagicMock()
        mock_geo.latlng = [45.0687, 7.6847]
        stay = StayFactory.build(latitude=None, longitude=None)
        with patch(
            "trips.models.geocoder.mapbox", return_value=mock_geo
        ) as mock_mapbox:
            stay.save()
        mock_mapbox.assert_called_once()
        assert stay.latitude == 45.0687
        assert stay.longitude == 7.6847


class TestEventSaveSkipsGeocodingWhenCoordsProvided(TestCase):
    def test_experience_save_with_coords_skips_mapbox(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        experience = ExperienceFactory.build(
            trip=trip,
            latitude=45.0687,
            longitude=7.6847,
        )
        with patch("trips.models.geocoder.mapbox") as mock_geo:
            experience.save()
        mock_geo.assert_not_called()
        assert experience.latitude == 45.0687
        assert experience.longitude == 7.6847

    def test_meal_save_with_coords_skips_mapbox(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        meal = MealFactory.build(
            trip=trip,
            latitude=45.0712,
            longitude=7.6858,
        )
        with patch("trips.models.geocoder.mapbox") as mock_geo:
            meal.save()
        mock_geo.assert_not_called()
        assert meal.latitude == 45.0712
        assert meal.longitude == 7.6858

    def test_experience_save_without_coords_calls_mapbox(self):
        user = self.make_user("user@example.com")
        trip = TripFactory(author=user)
        mock_geo = MagicMock()
        mock_geo.latlng = [45.0687, 7.6847]
        experience = ExperienceFactory.build(
            trip=trip,
            latitude=None,
            longitude=None,
        )
        with patch("trips.models.geocoder.mapbox", return_value=mock_geo):
            experience.save()
        assert experience.latitude == 45.0687
        assert experience.longitude == 7.6847


class TestTripMapStagesContext(TestCase):
    """trip_map view passes stage context variables."""

    def test_map_view_passes_stages_context(self):
        user = self.make_user("stages_ctx@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        self.response_200(response)
        assert "stages" in response.context
        assert "has_custom_stages" in response.context

    def test_has_custom_stages_false_when_only_main_stage(self):
        user = self.make_user("no_custom@example.com")
        trip = TripFactory(author=user, destination="Roma")
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        assert response.context["has_custom_stages"] is False

    def test_has_custom_stages_true_when_custom_stage_exists(self):
        user = self.make_user("has_custom@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        with self.login(user):
            response = self.get("trips:trip-map", pk=trip.pk)
        assert response.context["has_custom_stages"] is True


class TestTripDestinationsView(TestCase):
    def test_owner_gets_destinations_modal(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)
        self.response_200(response)
        assert response.context["trip"] == trip
        assert "stages" in response.context

    def test_other_user_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)
        self.response_404(response)

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        response = self.get("trips:trip-destinations", trip_pk=trip.pk)
        self.response_302(response)


class TestCreateStageView(TestCase):
    def test_get_returns_create_stage_form(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:create-stage", trip_pk=trip.pk)
        self.response_200(response)
        assert response.context["trip"] == trip
        assert "days" in response.context

    def test_post_creates_stage_with_destination(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with self.login(user):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze", "days": [day.pk]},
            )
        self.response_200(response)
        day.refresh_from_db()
        assert day.destination == "Firenze"

    def test_post_with_coords_updates_day(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": "Firenze",
                    "destination_latitude": "43.7696",
                    "destination_longitude": "11.2558",
                    "days": [day.pk],
                },
            )
        day.refresh_from_db()
        assert day.destination == "Firenze"
        assert day.destination_latitude == 43.7696

    def test_post_with_invalid_coords_ignores_coords(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": "Firenze",
                    "destination_latitude": "not-a-float",
                    "destination_longitude": "also-not",
                    "days": [day.pk],
                },
            )
        day.refresh_from_db()
        assert day.destination == "Firenze"
        assert day.destination_latitude is None

    def test_post_without_destination_does_nothing(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        original_destination = day.destination
        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "", "days": [day.pk]},
            )
        day.refresh_from_db()
        assert day.destination == original_destination

    def test_post_with_already_staged_day_skips_update(self):
        """Covers 252->268: affected_numbers is empty when all days already in custom stage."""
        from datetime import date, timedelta

        user = self.make_user("staged_day@example.com")
        trip = TripFactory(
            author=user,
            destination="Roma",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "Napoli", "days": [day.pk]},
            )
        day.refresh_from_db()
        assert day.destination == "Firenze"

    def test_post_with_last_day_no_next_day(self):
        """Covers 266->268: first_of_next is None when last day of trip is selected."""
        from datetime import date, timedelta

        user = self.make_user("last_day@example.com")
        trip = TripFactory(
            author=user,
            destination="Roma",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        last_day = trip.days.order_by("number").last()
        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze", "days": [last_day.pk]},
            )
        last_day.refresh_from_db()
        assert last_day.destination == "Firenze"

    def test_non_editor_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("trips:create-stage", trip_pk=trip.pk)
        self.response_404(response)


class TestDeleteStageView(TestCase):
    def test_post_deletes_stage_and_unassigns_events(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        Event.objects.create(
            trip=trip,
            day=day,
            name="Test Uffizi",
            address="Via Roma",
            category=Event.Category.EXPERIENCE,
        )
        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze"},
            )
        self.response_200(response)
        day.refresh_from_db()
        assert day.destination == "Roma"
        assert Event.objects.get(name="Test Uffizi").day is None

    def test_post_with_main_destination_does_nothing(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user, destination="Roma")
        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": "Roma"},
            )
        self.response_200(response)

    def test_post_without_destination_does_nothing(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": ""},
            )
        self.response_200(response)

    def test_delete_stage_with_next_day(self):
        """Covers async_task for first_of_next when a subsequent day exists."""
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user, destination="Roma")
        days = list(trip.days.order_by("number"))
        days[0].destination = "Firenze"
        days[0].save()
        with self.login(user):
            self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze"},
            )
        days[0].refresh_from_db()
        assert days[0].destination == "Roma"

    def test_get_returns_destinations_modal(self):
        """Covers 289->312: GET request to delete_stage (non-POST branch)."""
        user = self.make_user("owner_get@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:delete-stage", trip_pk=trip.pk)
        self.response_200(response)
        assert "stages" in response.context

    def test_delete_last_stage_no_next_day(self):
        """Covers 310->312: first_of_next is None when stage includes the last trip day."""
        from datetime import date, timedelta

        user = self.make_user("del_last@example.com")
        trip = TripFactory(
            author=user,
            destination="Roma",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        last_day = trip.days.order_by("number").last()
        last_day.destination = "Firenze"
        last_day.save()
        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze"},
            )
        self.response_200(response)
        last_day.refresh_from_db()
        assert last_day.destination == "Roma"

    def test_non_editor_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze"},
            )
        self.response_404(response)


class TestUpdateDayDestinationView(TestCase):
    def test_get_returns_day_destination_card(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with self.login(user):
            response = self.get(
                "trips:update-day-destination", trip_pk=trip.pk, day_pk=day.pk
            )
        self.response_200(response)
        assert response.context["day"] == day

    def test_post_updates_day_destination(self):
        user = self.make_user("owner@example.com")
        trip = TripFactory(author=user)
        day = trip.days.first()
        with self.login(user):
            response = self.post(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
                data={"destination": "Venezia"},
            )
        self.response_204(response)
        day.refresh_from_db()
        assert day.destination == "Venezia"

    def test_non_editor_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = TripFactory(author=owner)
        day = trip.days.first()
        with self.login(other):
            response = self.get(
                "trips:update-day-destination", trip_pk=trip.pk, day_pk=day.pk
            )
        self.response_404(response)


class TestGeocodeAddressView(TestCase):
    def test_post_with_name_and_city_returns_results(self):
        user = self.make_user("user@example.com")
        mock_results = [
            {"display_name": "Via Roma 1, Torino", "lat": "45.07", "lon": "7.68"}
        ]
        with self.login(user):
            with patch("trips.views.maps.geocode_location", return_value=mock_results):
                response = self.post(
                    "trips:geocode-address",
                    data={"name": "Via Roma", "city": "Torino"},
                )
        self.response_200(response)
        assert response.context["found"] is True

    def test_post_with_no_results_returns_not_found(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            with patch("trips.views.maps.geocode_location", return_value=[]):
                response = self.post(
                    "trips:geocode-address",
                    data={"name": "Posto Inesistente", "city": "Torino"},
                )
        self.response_200(response)
        assert response.context["found"] is False

    def test_post_without_name_returns_not_found(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.post(
                "trips:geocode-address",
                data={"name": "", "city": "Torino"},
            )
        self.response_200(response)
        assert response.context["found"] is False

    def test_get_returns_not_found(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.get("trips:geocode-address")
        self.response_200(response)
        assert response.context["found"] is False


class TestGeocodeCityView(TestCase):
    def test_post_with_query_returns_results(self):
        user = self.make_user("user@example.com")
        mock_cities = [
            {"display_name": "Firenze, Toscana, Italia", "lat": "43.77", "lon": "11.25"}
        ]
        with self.login(user):
            with patch("trips.views.maps.geocode_city", return_value=mock_cities):
                response = self.post(
                    "trips:geocode-city",
                    data={"destination": "Firenze"},
                )
        self.response_200(response)
        assert response.context["found"] is True

    def test_post_empty_query_returns_not_found(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.post(
                "trips:geocode-city",
                data={"destination": ""},
            )
        self.response_200(response)
        assert response.context["found"] is False

    def test_get_returns_not_found(self):
        user = self.make_user("user@example.com")
        with self.login(user):
            response = self.get("trips:geocode-city")
        self.response_200(response)
        assert response.context["found"] is False


class TestStageBiasInternal(TestCase):
    """Direct tests for _stage_location_bias internal branches via map_search."""

    def test_stage_bias_uses_event_coords(self):
        """Stage has events with coords → centroid computed from them."""
        user = self.make_user("stage_event@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        Event.objects.create(
            trip=trip,
            day=day,
            name="Uffizi",
            address="Piazzale degli Uffizi, Firenze",
            latitude=43.768,
            longitude=11.255,
            category=Event.Category.EXPERIENCE,
        )
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post(
                    "trips:map-search",
                    pk=trip.pk,
                    data={"query": "museo", "stage_destination": "Firenze"},
                )
        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None
        lat, _, _ = call_kwargs["location_bias"]
        assert abs(lat - 43.768) < 0.01

    def test_stage_bias_uses_day_destination_coords(self):
        """Stage has no events but day has destination coords → centroid from day."""
        user = self.make_user("stage_day@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.destination_latitude = 43.77
        day.destination_longitude = 11.25
        day.save()
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                MockClient.return_value.search_text.return_value = []
                self.post(
                    "trips:map-search",
                    pk=trip.pk,
                    data={"query": "museo", "stage_destination": "Firenze"},
                )
        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None

    def test_stage_bias_geocoder_fallback(self):
        """No coords for stage → geocoder fallback used."""
        user = self.make_user("stage_geocoder@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        mock_geo = MagicMock()
        mock_geo.latlng = [43.77, 11.25]
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch(
                    "trips.views.maps.geocoder.mapbox", return_value=mock_geo
                ) as mock_mapbox:
                    MockClient.return_value.search_text.return_value = []
                    self.post(
                        "trips:map-search",
                        pk=trip.pk,
                        data={"query": "museo", "stage_destination": "Firenze"},
                    )
        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert call_kwargs["location_bias"] is not None
        assert call_kwargs["location_bias"][2] == 50_000
        # place-level lookup so an ambiguous stage name cannot match a country
        assert mock_mapbox.call_args.kwargs["types"] == "place"

    def test_stage_bias_falls_back_to_trip_bias_when_geocoder_fails(self):
        """Stage geocoder fails → falls back to _trip_location_bias."""
        user = self.make_user("stage_fallback@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        mock_geo_fail = MagicMock()
        mock_geo_fail.latlng = None
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch(
                    "trips.views.maps.geocoder.mapbox", return_value=mock_geo_fail
                ):
                    MockClient.return_value.search_text.return_value = []
                    self.post(
                        "trips:map-search",
                        pk=trip.pk,
                        data={"query": "museo", "stage_destination": "Firenze"},
                    )
        call_kwargs = MockClient.return_value.search_text.call_args.kwargs
        assert "location_bias" in call_kwargs


class TestMapSearchStageBias(TestCase):
    """map_search uses stage_destination to set location_bias."""

    def test_search_without_stage_uses_trip_bias(self):
        user = self.make_user("no_stage@example.com")
        trip = TripFactory(author=user)
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch("trips.views.maps._trip_location_bias") as mock_trip_bias:
                    with patch(
                        "trips.views.maps._stage_location_bias"
                    ) as mock_stage_bias:
                        MockClient.return_value.search_text.return_value = []
                        mock_trip_bias.return_value = (45.0, 7.0, 10_000)
                        self.post(
                            "trips:map-search", pk=trip.pk, data={"query": "museo"}
                        )
        mock_trip_bias.assert_called_once_with(trip)
        mock_stage_bias.assert_not_called()

    def test_search_with_stage_uses_stage_bias(self):
        user = self.make_user("with_stage@example.com")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        with self.login(user):
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch("trips.views.maps._stage_location_bias") as mock_stage_bias:
                    MockClient.return_value.search_text.return_value = []
                    mock_stage_bias.return_value = (43.7, 11.25, 10_000)
                    self.post(
                        "trips:map-search",
                        pk=trip.pk,
                        data={"query": "museo", "stage_destination": "Firenze"},
                    )
        mock_stage_bias.assert_called_once_with(trip, "Firenze")
