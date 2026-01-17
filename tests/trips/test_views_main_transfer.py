import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import MainTransferFactory, TripFactory

pytestmark = pytest.mark.django_db


class TestMainTransferViews(TestCase):
    """Tests for main transfer CRUD views"""

    def test_edit_main_transfer_get(self):
        """Test GET request to edit main transfer shows form"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        # Use type=1 (PLANE) to have predictable template
        transfer = MainTransferFactory(trip=trip, direction=1, type=1)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/main-transfer-flight.html")
            assert response.context["is_edit"] is True

    def test_edit_main_transfer_post_valid(self):
        """Test POST request updates main transfer"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        # Use type=2 (TRAIN) - must provide valid train form fields
        transfer = MainTransferFactory(trip=trip, direction=1, type=2)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        data = {
            "direction": 1,
            "origin_station": "Florence Central Station",  # Changed
            "origin_station_id": "12345",
            "origin_latitude": "43.776",
            "origin_longitude": "11.247",
            "destination_station": "Rome Termini",
            "destination_station_id": "67890",
            "destination_latitude": "41.901",
            "destination_longitude": "12.502",
            "start_time": "14:00",  # Changed
            "end_time": "15:30",
            "company": "Trenitalia",
            "train_number": "FR9612",
        }

        with self.login(user):
            response = self.client.post(url, data)

            assert response.status_code == 204
            transfer.refresh_from_db()
            assert transfer.origin_name == "Florence Central Station"
            assert str(transfer.start_time) == "14:00:00"

    def test_edit_main_transfer_non_owner_404(self):
        """Test editing main transfer by non-owner returns 404"""
        user = self.make_user("user")
        other_trip = TripFactory()  # Different user
        transfer = MainTransferFactory(trip=other_trip, direction=1)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 404

    def test_delete_main_transfer(self):
        """Test deleting main transfer"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1)
        url = reverse("trips:delete-main-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.post(url)

            assert response.status_code == 204
            assert response.headers.get("HX-Refresh") == "true"
            from trips.models import MainTransfer

            assert not MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_delete_main_transfer_non_owner_404(self):
        """Test deleting main transfer by non-owner returns 404"""
        user = self.make_user("user")
        other_trip = TripFactory()
        transfer = MainTransferFactory(trip=other_trip, direction=1)
        url = reverse("trips:delete-main-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.post(url)

            assert response.status_code == 404

    def test_edit_main_transfer_post_invalid(self):
        """Test editing with invalid data shows form with errors"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        # Use type=2 (TRAIN) for predictable template
        transfer = MainTransferFactory(trip=trip, direction=1, type=2)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        # Invalid data - missing required fields for train form
        data = {
            "direction": 1,
            "origin_station": "",  # Empty - should fail validation
            "destination_station": "",  # Empty - should fail validation
            "start_time": "10:00",
            "end_time": "11:30",
        }

        with self.login(user):
            response = self.client.post(url, data)

            # Should return form with errors
            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/main-transfer-train.html")
            assert "form" in response.context
            assert response.context["form"].errors

    def test_search_airports_post_with_results(self):
        """Test searching for airports returns results"""
        user = self.make_user("user")
        url = reverse("trips:search-airports")

        with self.login(user):
            response = self.client.post(url, {"airport_query": "Milan"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/airport-results.html")
            assert response.context["found"] is True
            assert len(response.context["airports"]) > 0

    def test_search_airports_post_no_results_short_query(self):
        """Test searching for airports with query too short"""
        user = self.make_user("user")
        url = reverse("trips:search-airports")

        with self.login(user):
            response = self.client.post(url, {"airport_query": "X"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/airport-results.html")
            assert response.context["found"] is False

    def test_search_airports_post_no_matching_results(self):
        """Test searching for airports with valid query but no matches"""
        user = self.make_user("user")
        url = reverse("trips:search-airports")

        with self.login(user):
            response = self.client.post(url, {"airport_query": "XYZ12345NotExist"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/airport-results.html")
            assert response.context["found"] is False

    def test_search_airports_get_returns_empty(self):
        """Test GET request to search airports returns empty state"""
        user = self.make_user("user")
        url = reverse("trips:search-airports")

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/airport-results.html")
            assert response.context["found"] is False
            assert response.context["field_type"] == "origin"

    def test_search_stations_post_with_results(self):
        """Test searching for train stations returns results"""
        user = self.make_user("user")
        url = reverse("trips:search-stations")

        with self.login(user):
            response = self.client.post(url, {"station_query": "Paris"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/station-results.html")
            assert response.context["found"] is True
            assert len(response.context["stations"]) > 0

    def test_search_stations_post_no_results_short_query(self):
        """Test searching for stations with query too short"""
        user = self.make_user("user")
        url = reverse("trips:search-stations")

        with self.login(user):
            response = self.client.post(url, {"station_query": "X"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/station-results.html")
            assert response.context["found"] is False

    def test_search_stations_post_no_matching_results(self):
        """Test searching for stations with valid query but no matches"""
        user = self.make_user("user")
        url = reverse("trips:search-stations")

        with self.login(user):
            response = self.client.post(url, {"station_query": "XYZ12345NotExist"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/station-results.html")
            assert response.context["found"] is False

    def test_search_stations_get_returns_empty(self):
        """Test GET request to search stations returns empty state"""
        user = self.make_user("user")
        url = reverse("trips:search-stations")

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/station-results.html")
            assert response.context["found"] is False
            assert response.context["field_type"] == "origin"

    def test_main_transfers_section(self):
        """Test main transfers section view"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        arrival = MainTransferFactory(trip=trip, direction=1, type=1)
        departure = MainTransferFactory(trip=trip, direction=2, type=1)
        url = reverse("trips:main-transfers-section", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/includes/main-transfers.html")
            assert response.context["trip"] == trip
            assert response.context["arrival_transfer"] == arrival
            assert response.context["departure_transfer"] == departure

    def test_arrival_transfer_modal(self):
        """Test arrival transfer modal"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:arrival-transfer-modal", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/arrival-transfer-modal.html")
            assert response.context["trip"] == trip
            assert response.context["transport_type"] == 1  # PLANE default

    def test_departure_transfer_modal(self):
        """Test departure transfer modal"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:departure-transfer-modal", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/departure-transfer-modal.html")
            assert response.context["trip"] == trip
            assert response.context["transport_type"] == 1  # PLANE default

    def test_main_transfer_step_type(self):
        """Test main transfer step - type selection"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url, {"step": "type"})

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/main-transfer-type.html")
            assert response.context["trip"] == trip

    def test_main_transfer_step_arrival_plane(self):
        """Test main transfer step - arrival with plane type"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "plane", "direction": "arrival"},
            )

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/main-transfer-flight.html")
            assert response.context["trip"] == trip
            assert response.context["direction"] == "arrival"

    def test_main_transfer_step_departure_train(self):
        """Test main transfer step - departure with train type"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url, {"step": "departure", "transport_type": "train"}
            )

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/main-transfer-train.html")
            assert response.context["trip"] == trip
            assert response.context["direction"] == "departure"

    def test_main_transfer_step_invalid(self):
        """Test main transfer step with invalid step"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url, {"step": "invalid"})

            assert response.status_code == 400

    def test_save_main_transfer_arrival(self):
        """Test saving arrival transfer closes modal"""
        from trips.models import MainTransfer

        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:save-main-transfer", kwargs={"trip_id": trip.pk})

        data = {
            "direction": 1,  # ARRIVAL
            "origin_airport": "Rome Fiumicino",
            "origin_iata": "FCO",
            "origin_latitude": "41.8003",
            "origin_longitude": "12.2389",
            "destination_airport": "Milan Malpensa",
            "destination_iata": "MXP",
            "destination_latitude": "45.6306",
            "destination_longitude": "8.7281",
            "start_time": "10:00",
            "end_time": "11:30",
            "flight_number": "AZ123",
        }

        with self.login(user):
            response = self.client.post(
                url, data, QUERY_STRING="transport_type=plane&direction=arrival"
            )

            # Should create transfer and close modal
            assert response.status_code == 204
            assert "HX-Trigger" in response.headers
            # Verify arrival was created
            assert MainTransfer.objects.filter(
                trip=trip, direction=MainTransfer.Direction.ARRIVAL
            ).exists()

    def test_save_main_transfer_departure(self):
        """Test saving departure transfer closes modal"""

        user = self.make_user("user")
        trip = TripFactory(author=user)
        # Create arrival first
        MainTransferFactory(trip=trip, direction=1, type=1)
        url = reverse("trips:save-main-transfer", kwargs={"trip_id": trip.pk})

        data = {
            "direction": 2,  # DEPARTURE
            "origin_airport": "Milan Malpensa",
            "origin_iata": "MXP",
            "origin_latitude": "45.6306",
            "origin_longitude": "8.7281",
            "destination_airport": "Rome Fiumicino",
            "destination_iata": "FCO",
            "destination_latitude": "41.8003",
            "destination_longitude": "12.2389",
            "start_time": "18:00",
            "end_time": "19:30",
            "flight_number": "AZ456",
        }

        with self.login(user):
            response = self.client.post(
                url, data, QUERY_STRING="transport_type=plane&direction=departure"
            )

            assert response.status_code == 204
            assert "HX-Trigger" in response.headers

    def test_save_main_transfer_invalid_method(self):
        """Test save main transfer with GET returns 405"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:save-main-transfer", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 405

    def test_save_main_transfer_invalid_data(self):
        """Test save main transfer with invalid form data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:save-main-transfer", kwargs={"trip_id": trip.pk})

        # Missing required fields
        data = {}

        with self.login(user):
            response = self.client.post(
                url, data, QUERY_STRING="transport_type=plane&direction=arrival"
            )

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/main-transfer-flight.html")
            assert "form" in response.context
            assert response.context["form"].errors
