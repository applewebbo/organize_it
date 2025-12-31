import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import MainTransferFactory, TripFactory

pytestmark = pytest.mark.django_db


class TestMainTransferViews(TestCase):
    """Tests for main transfer CRUD views"""

    def test_add_main_transfer_get(self):
        """Test GET request to add main transfer shows form"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:add-main-transfer", kwargs={"trip_id": trip.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/main-transfer-form.html")
            assert "form" in response.context
            assert response.context["trip"] == trip

    def test_add_main_transfer_post_valid(self):
        """Test POST request creates main transfer"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:add-main-transfer", kwargs={"trip_id": trip.pk})

        data = {
            "type": 2,  # PLANE
            "direction": 1,  # ARRIVAL
            "origin_city": "Milan",
            "origin_address": "Malpensa Airport",
            "destination_city": trip.destination,
            "destination_address": "Hotel Roma",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        with self.login(user):
            response = self.client.post(url, data)

            assert response.status_code == 204
            assert response.headers.get("HX-Trigger") == "tripModified"

            # Verify transfer was created
            from trips.models import Transport

            transfer = Transport.objects.filter(
                trip=trip, is_main_transfer=True
            ).first()
            assert transfer is not None
            assert transfer.direction == 1
            assert transfer.day is None

    def test_edit_main_transfer_get(self):
        """Test GET request to edit main transfer shows form"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/main-transfer-form.html")
            assert response.context["transfer"] == transfer
            assert response.context["is_edit"] is True

    def test_edit_main_transfer_post_valid(self):
        """Test POST request updates main transfer"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=2)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        data = {
            "type": 2,
            "direction": 1,
            "origin_city": "Florence",  # Changed
            "origin_address": "Airport",
            "destination_city": trip.destination,
            "destination_address": "Hotel",
            "start_time": "14:00",  # Changed
            "end_time": "15:30",
        }

        with self.login(user):
            response = self.client.post(url, data)

            assert response.status_code == 204
            transfer.refresh_from_db()
            assert transfer.origin_city == "Florence"
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
            from trips.models import Transport

            assert not Transport.objects.filter(pk=transfer.pk).exists()

    def test_delete_main_transfer_non_owner_404(self):
        """Test deleting main transfer by non-owner returns 404"""
        user = self.make_user("user")
        other_trip = TripFactory()
        transfer = MainTransferFactory(trip=other_trip, direction=1)
        url = reverse("trips:delete-main-transfer", kwargs={"pk": transfer.pk})

        with self.login(user):
            response = self.client.post(url)

            assert response.status_code == 404

    def test_get_transport_type_fields_plane(self):
        """Test getting plane-specific fields partial"""
        user = self.make_user("user")
        url = reverse("trips:transport-type-fields")

        with self.login(user):
            response = self.client.get(url, {"type": "2"})  # PLANE

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/flight-fields.html")
            content = response.content.decode()
            assert "flight_number" in content
            assert "gate" in content
            assert "terminal" in content

    def test_get_transport_type_fields_train(self):
        """Test getting train-specific fields partial"""
        user = self.make_user("user")
        url = reverse("trips:transport-type-fields")

        with self.login(user):
            response = self.client.post(url, {"type": "3"})  # TRAIN

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/train-fields.html")
            content = response.content.decode()
            assert "train_number" in content
            assert "carriage" in content
            assert "seat" in content

    def test_get_transport_type_fields_car(self):
        """Test getting car-specific fields partial"""
        user = self.make_user("user")
        url = reverse("trips:transport-type-fields")

        with self.login(user):
            response = self.client.get(url, {"type": "1"})  # CAR

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/car-fields.html")
            content = response.content.decode()
            assert "license_plate" in content
            assert "car_type" in content
            assert "is_rental" in content

    def test_get_transport_type_fields_generic(self):
        """Test getting generic fields for other transport types"""
        user = self.make_user("user")
        url = reverse("trips:transport-type-fields")

        with self.login(user):
            response = self.client.get(url, {"type": "5"})  # BUS

            assert response.status_code == 200
            assertTemplateUsed(response, "trips/partials/generic-transport-fields.html")

    def test_get_transport_type_fields_no_type(self):
        """Test getting fields without type returns empty"""
        user = self.make_user("user")
        url = reverse("trips:transport-type-fields")

        with self.login(user):
            response = self.client.get(url)

            assert response.status_code == 200
            assert response.content == b""

    def test_add_main_transfer_post_invalid(self):
        """Test POST with invalid data shows form with errors"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        url = reverse("trips:add-main-transfer", kwargs={"trip_id": trip.pk})

        # Missing required fields
        data = {
            "type": 2,
            "direction": 1,
            # Missing origin_city, destination_city, times
        }

        with self.login(user):
            response = self.client.post(url, data)

            # Should return form with errors, not 204
            assert response.status_code == 200
            assertTemplateUsed(response, "trips/main-transfer-form.html")
            assert "form" in response.context
            assert response.context["form"].errors

    def test_edit_main_transfer_post_invalid(self):
        """Test editing with invalid data shows form with errors"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        transfer = MainTransferFactory(trip=trip, direction=1, type=2)
        url = reverse("trips:edit-main-transfer", kwargs={"pk": transfer.pk})

        # Invalid data - empty origin_city
        data = {
            "type": 2,
            "direction": 1,
            "origin_city": "",  # Empty - should fail validation
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        with self.login(user):
            response = self.client.post(url, data)

            # Should return form with errors
            assert response.status_code == 200
            assertTemplateUsed(response, "trips/main-transfer-form.html")
            assert "form" in response.context
            assert response.context["form"].errors
