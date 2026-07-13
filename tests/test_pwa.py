import pytest
from django.template.loader import render_to_string
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db

PLACEHOLDER_TEXT = "Map not available offline"


class TestPWAEndpoints(TestCase):
    def test_manifest_is_public_and_json(self):
        response = self.get("manifest")

        self.response_200(response)
        assert response["Content-Type"].startswith("application/json")
        assert "Organize It" in response.content.decode()

    def test_service_worker_is_public_and_javascript(self):
        response = self.get("serviceworker")

        self.response_200(response)
        assert response["Content-Type"] == "application/javascript"
        body = response.content.decode()
        assert "networkFirst" in body
        assert "/offline/" in body

    def test_offline_page_reachable_without_login(self):
        response = self.get("offline")

        self.response_200(response)
        assertTemplateUsed(response, "offline.html")
        assert "You are offline" in response.content.decode()


class TestPWAMeta(TestCase):
    def test_base_template_registers_pwa(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        content = response.content.decode()
        assert 'rel="manifest"' in content
        assert "serviceWorker" in content


class TestMapOfflinePlaceholder(TestCase):
    def test_trip_map_fragment_renders_placeholder_when_map_present(self):
        trip = TripFactory()
        html = render_to_string(
            "trips/includes/events-map-fragment.html",
            {"trip": trip, "map": "<div>folium</div>"},
        )

        assert PLACEHOLDER_TEXT in html
        # The real map is hidden while offline; the placeholder takes its place.
        assert 'x-show="$store.connection.online"' in html

    def test_trip_map_fragment_empty_state_has_no_placeholder(self):
        trip = TripFactory()
        html = render_to_string(
            "trips/includes/events-map-fragment.html",
            {"trip": trip, "map": None},
        )

        assert PLACEHOLDER_TEXT not in html

    def test_day_map_content_renders_placeholder_when_map_present(self):
        html = render_to_string(
            "trips/includes/day-map-content.html",
            {"map": "<div>folium</div>", "locations": {}},
        )

        assert PLACEHOLDER_TEXT in html

    def test_day_lazy_map_only_loads_when_online(self):
        html = render_to_string(
            "trips/includes/day.html",
            {"day": TripFactory().days.first(), "show_map": True, "map": None},
        )

        assert PLACEHOLDER_TEXT in html
        assert "load[navigator.onLine]" in html
