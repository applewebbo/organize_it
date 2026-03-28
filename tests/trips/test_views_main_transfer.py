from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    ExperienceFactory,
    MainTransferFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)

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


class TestTrainStatusRedirect(TestCase):
    """Tests for train_status_redirect view"""

    def test_non_owner_returns_404(self):
        """Test 404 for non-owner"""
        user = self.make_user("owner")
        other = self.make_user("other")
        transfer = MainTransferFactory(trip__author=user, type=2)
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(other):
            response = self.client.get(url)
        assert response.status_code == 404

    def test_non_train_type_returns_404(self):
        """Test 404 for non-train transfer"""
        user = self.make_user("user")
        transfer = MainTransferFactory(trip__author=user, type=1)  # PLANE
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(user):
            response = self.client.get(url)
        assert response.status_code == 404

    def test_with_train_number_success(self):
        """Redirect to specific train status page when train number matches"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={"train_number": "2822"},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.text = "2822 - ROMA TERMINI - 23/03/26|2822-S00219-1774220400000"
        with patch("trips.views.requests.get", return_value=mock_resp):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "treno=2822" in response["Location"]
        assert "origine=S00219" in response["Location"]

    def test_with_train_number_bad_response_falls_to_station(self):
        """Falls back to station board when train API returns bad format"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={"train_number": "9999"},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        train_resp = MagicMock()
        train_resp.ok = True
        train_resp.text = "badformat"  # No "|" separator with 3 parts

        station_resp = MagicMock()
        station_resp.ok = True
        station_resp.json.return_value = [{"id": "S00219", "nomeLungo": "ROMA TERMINI"}]

        with patch("trips.views.requests.get", side_effect=[train_resp, station_resp]):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "cod=S00219" in response["Location"]

    def test_with_train_number_exception_falls_to_station(self):
        """Falls back to station board when train API raises exception"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={"train_number": "2822"},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        station_resp = MagicMock()
        station_resp.ok = True
        station_resp.json.return_value = [{"id": "S00219", "nomeLungo": "ROMA TERMINI"}]

        with patch(
            "trips.views.requests.get", side_effect=[Exception("timeout"), station_resp]
        ):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "cod=S00219" in response["Location"]

    def test_without_train_number_station_board(self):
        """Redirect to station departure board when no train number"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        station_resp = MagicMock()
        station_resp.ok = True
        station_resp.json.return_value = [{"id": "S00219", "nomeLungo": "ROMA TERMINI"}]

        with patch("trips.views.requests.get", return_value=station_resp):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "cod=S00219" in response["Location"]

    def test_station_api_exception_fallback_homepage(self):
        """Falls back to viaggiatreno homepage when station API fails"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        with patch("trips.views.requests.get", side_effect=Exception("timeout")):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "home.jsp" in response["Location"]

    def test_station_api_empty_list_fallback_homepage(self):
        """Falls back to viaggiatreno homepage when station API returns empty list"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        station_resp = MagicMock()
        station_resp.ok = True
        station_resp.json.return_value = []

        with patch("trips.views.requests.get", return_value=station_resp):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "home.jsp" in response["Location"]

    def test_with_train_number_empty_text_falls_to_station(self):
        """Falls back to station board when train API returns empty text"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={"train_number": "2822"},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        train_resp = MagicMock()
        train_resp.ok = True
        train_resp.text = ""  # Empty text → skip to station fallback

        station_resp = MagicMock()
        station_resp.ok = True
        station_resp.json.return_value = [{"id": "S00219", "nomeLungo": "ROMA TERMINI"}]

        with patch("trips.views.requests.get", side_effect=[train_resp, station_resp]):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "cod=S00219" in response["Location"]

    def test_station_api_not_ok_fallback_homepage(self):
        """Falls back to homepage when station API returns non-ok response"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=2,
            origin_name="ROMA TERMINI",
            type_specific_data={},
        )
        url = reverse("trips:train-status-redirect", kwargs={"pk": transfer.pk})

        station_resp = MagicMock()
        station_resp.ok = False  # Not ok → skip to homepage

        with patch("trips.views.requests.get", return_value=station_resp):
            with self.login(user):
                response = self.client.get(url)
        assert response.status_code == 302
        assert "home.jsp" in response["Location"]


class TestFlightStatusRedirect(TestCase):
    """Tests for flight_status_redirect view"""

    def test_non_owner_returns_404(self):
        """Test 404 for non-owner"""
        user = self.make_user("owner")
        other = self.make_user("other")
        transfer = MainTransferFactory(trip__author=user, type=1)
        url = reverse("trips:flight-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(other):
            response = self.client.get(url)
        assert response.status_code == 404

    def test_non_plane_type_returns_404(self):
        """Test 404 for non-plane transfer"""
        user = self.make_user("user")
        transfer = MainTransferFactory(trip__author=user, type=2)  # TRAIN
        url = reverse("trips:flight-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(user):
            response = self.client.get(url)
        assert response.status_code == 404

    def test_with_flight_number_redirects_to_flight_page(self):
        """Redirect to specific flight status page when flight number is set"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=1,
            origin_code="MXP",
            type_specific_data={"flight_number": "AZ1234"},
        )
        url = reverse("trips:flight-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(user):
            response = self.client.get(url)
        assert response.status_code == 302
        assert response["Location"] == "https://it.flightaware.com/live/flight/AZ1234"

    def test_without_flight_number_with_icao_redirects_to_airport(self):
        """Redirect to airport board when no flight number but ICAO available"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=1,
            origin_code="MXP",  # MXP → LIMC in CSV
            type_specific_data={},
        )
        url = reverse("trips:flight-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(user):
            response = self.client.get(url)
        assert response.status_code == 302
        assert response["Location"] == "https://it.flightaware.com/live/airport/LIMC"

    def test_without_flight_number_no_icao_redirects_to_homepage(self):
        """Redirect to FlightAware homepage when no flight number and no ICAO"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=1,
            origin_code="XXXX",  # Unknown IATA → no ICAO
            type_specific_data={},
        )
        url = reverse("trips:flight-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(user):
            response = self.client.get(url)
        assert response.status_code == 302
        assert response["Location"] == "https://it.flightaware.com"

    def test_without_flight_number_no_origin_code_redirects_to_homepage(self):
        """Redirect to FlightAware homepage when no origin code at all"""
        user = self.make_user("user")
        transfer = MainTransferFactory(
            trip__author=user,
            type=1,
            origin_code="",
            type_specific_data={},
        )
        url = reverse("trips:flight-status-redirect", kwargs={"pk": transfer.pk})
        with self.login(user):
            response = self.client.get(url)
        assert response.status_code == 302
        assert response["Location"] == "https://it.flightaware.com"


class TestCarTransferQuickFill(TestCase):
    """Tests for quick-fill location list in car/other main transfer forms"""

    def test_car_arrival_quick_fill_includes_day1_stay(self):
        """quick_fill_locations includes stay from day 1 for arrival direction"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.order_by("date").first()
        stay = StayFactory(day=day1)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        addresses = [loc["address"] for loc in locations]
        assert stay.address in addresses
        stay_loc = next(loc for loc in locations if loc["address"] == stay.address)
        assert stay_loc["type"] == "stay"

    def test_car_arrival_quick_fill_includes_day1_events(self):
        """quick_fill_locations includes events from day 1 for arrival direction"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.order_by("date").first()
        event = ExperienceFactory(trip=trip, day=day1, address="Via Test 1, Roma")
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        addresses = [loc["address"] for loc in locations]
        assert event.address in addresses
        exp_loc = next(loc for loc in locations if loc["address"] == event.address)
        assert exp_loc["type"] == "experience"

    def test_car_arrival_fallback_to_trip_destination_when_no_events(self):
        """quick_fill_locations falls back to trip.destination when day 1 has no stay/events"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        assert len(locations) == 1
        assert locations[0]["address"] == trip.destination
        assert locations[0]["type"] == "destination"

    def test_car_departure_quick_fill_includes_last_day_stay(self):
        """quick_fill_locations includes stay from last day for departure direction"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        last_day = trip.days.order_by("-date").first()
        stay = StayFactory(day=last_day)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {
                    "step": "departure",
                    "transport_type": "car",
                    "direction": "departure",
                },
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        addresses = [loc["address"] for loc in locations]
        assert stay.address in addresses
        stay_loc = next(loc for loc in locations if loc["address"] == stay.address)
        assert stay_loc["type"] == "stay"

    def test_car_departure_fallback_to_trip_destination_when_no_events(self):
        """quick_fill_locations falls back to trip.destination when last day has no stay/events"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {
                    "step": "departure",
                    "transport_type": "car",
                    "direction": "departure",
                },
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        assert len(locations) == 1
        assert locations[0]["address"] == trip.destination
        assert locations[0]["type"] == "destination"

    def test_car_arrival_home_address_in_form_initial(self):
        """origin_address is pre-filled with profile.home_address for arrival"""
        user = self.make_user("user")
        user.profile.home_address = "Via Casa 10, Milano"
        user.profile.save()
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        form = response.context["form"]
        assert form.fields["origin_address"].initial == "Via Casa 10, Milano"

    def test_car_departure_home_address_in_form_initial(self):
        """destination_address is pre-filled with profile.home_address for departure"""
        user = self.make_user("user")
        user.profile.home_address = "Via Casa 10, Milano"
        user.profile.save()
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {
                    "step": "departure",
                    "transport_type": "car",
                    "direction": "departure",
                },
            )

        assert response.status_code == 200
        form = response.context["form"]
        assert form.fields["destination_address"].initial == "Via Casa 10, Milano"

    def test_car_arrival_fallback_when_trip_has_no_days(self):
        """quick_fill_locations falls back to trip.destination when trip has no days"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        trip.days.all().delete()
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        assert len(locations) == 1
        assert locations[0]["address"] == trip.destination

    def test_car_arrival_skips_events_without_address(self):
        """Events without address are excluded from quick_fill_locations"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.order_by("date").first()
        # Create experience with no address
        ExperienceFactory(trip=trip, day=day1, address="")
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        # Event with empty address should not appear; fallback to trip.destination
        assert len(locations) == 1
        assert locations[0]["address"] == trip.destination

    def test_car_arrival_meal_type_in_quick_fill(self):
        """Meal events get type='meal' in quick_fill_locations"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.order_by("date").first()
        meal = MealFactory(trip=trip, day=day1, address="Via del Ristorante 5, Roma")
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "car", "direction": "arrival"},
            )

        assert response.status_code == 200
        locations = response.context["quick_fill_locations"]
        meal_loc = next(loc for loc in locations if loc["address"] == meal.address)
        assert meal_loc["type"] == "meal"


class TestOtherTransferView(TestCase):
    """Tests for OTHER main transfer view — no quick-fill, no home address"""

    def test_other_transfer_no_quick_fill_locations(self):
        """quick_fill_locations is empty for OTHER transport type"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.order_by("date").first()
        StayFactory(day=day1)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "other", "direction": "arrival"},
            )

        assert response.status_code == 200
        assert response.context["quick_fill_locations"] == []

    def test_other_transfer_no_home_address_in_context(self):
        """home_address is not passed to form for OTHER transport"""
        user = self.make_user("user")
        user.profile.home_address = "Via Casa 10, Milano"
        user.profile.save()
        trip = TripFactory(author=user)
        url = reverse("trips:main-transfer-step", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(
                url,
                {"step": "arrival", "transport_type": "other", "direction": "arrival"},
            )

        assert response.status_code == 200
        form = response.context["form"]
        assert form.fields["origin_address"].initial is None
