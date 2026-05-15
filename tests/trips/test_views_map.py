from unittest.mock import MagicMock, patch

import pytest

from tests.test import TestCase
from tests.trips.factories import (
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.models import Event, Stay
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
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
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
            with patch("trips.views.maps.GooglePlacesClient") as MockClient:
                with patch("trips.views.maps.geocoder.mapbox", return_value=mock_geo):
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


class TripEventsMapFragmentTest(TestCase):
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


class TripEventsListFragmentTest(TestCase):
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


class SelectDayForEventTest(TestCase):
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


class ResolveMapsLinkViewTest(TestCase):
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


class StaySaveSkipsGeocodingWhenCoordsProvidedTest(TestCase):
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


class EventSaveSkipsGeocodingWhenCoordsProvidedTest(TestCase):
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
