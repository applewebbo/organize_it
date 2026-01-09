import datetime
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import StayFactory, TripFactory
from trips.models import Stay

pytestmark = pytest.mark.django_db


class AddStayView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        day = days.first()
        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay added successfully"
        day.refresh_from_db()
        assert day.stay is not None

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Hotel",
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-create.html")
        assert day.stay is None

    @patch("geocoder.mapbox")
    def test_post_single_day(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        first_day = days.first()
        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [first_day.pk],  # Only apply to first day
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=first_day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay added successfully"

        # Refresh days from db and verify
        first_day.refresh_from_db()
        assert first_day.stay is not None

        # Other days should not have the stay
        other_days = days.exclude(pk=first_day.pk)
        for day in other_days:
            day.refresh_from_db()
            assert day.stay is None


class StayDetailView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        # Create stay and set days after creation
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-detail", pk=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-detail.html")
        assert response.context["stay"] == stay
        assert response.context["first_day"] == days.first()
        assert response.context["last_day"] == days.last()

    def test_get_with_previous_day(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.all())
        # Create stay and set only second day onwards
        stay = StayFactory()
        stay.days.set(days[1:])

        with self.login(user):
            response = self.get("trips:stay-detail", pk=stay.pk)

        self.response_200(response)
        assert (
            response.context["first_day"] == days[0]
        )  # Should be the day before first stay day
        assert response.context["last_day"] == days[-1]


class StayModifyView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        data = {
            "name": "Updated Hotel",
            "check_in": "15:00",
            "check_out": "10:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_200(response)
        assert response.context["modified"]
        stay.refresh_from_db()
        assert stay.name == "Updated Hotel"
        assert stay.check_in == datetime.time(15, 0)
        assert stay.check_out == datetime.time(10, 0)

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        data = {
            "name": "",  # Invalid: name is required
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-modify.html")


class StayDeleteView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-delete.html")
        assert response.context["stay"] == stay

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.post("trips:stay-delete", pk=stay.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay deleted successfully"
        # Refresh the day from the database to get the updated stay value
        first_day = days.first()
        first_day.refresh_from_db()
        assert not first_day.stay

    def test_get_with_single_other_stay(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])  # First two days
        other_stay.days.set(days[2:])  # Remaining days

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay.pk)

        self.response_200(response)
        assert response.context["show_dropdown"] is False
        assert response.context["other_stays"].count() == 1
        assert response.context["other_stays"].first() == other_stay

    def test_get_with_multiple_other_stays(self):
        """Test stay deletion view when there are multiple other stays available"""
        user = self.make_user("user")

        # Create a trip with exactly 6 days
        start_date = datetime.date(2024, 1, 1)  # Use fixed date instead of today
        end_date = start_date + datetime.timedelta(days=5)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)

        # Get all days and ensure we have exactly 6
        days = list(trip.days.all().order_by("date"))
        assert len(days) == 6, f"Expected 6 days, got {len(days)}"

        # Create stays
        stay_to_delete = StayFactory()
        other_stay1 = StayFactory()
        other_stay2 = StayFactory()

        # Assign exactly 2 days to each stay
        stay_to_delete.days.set(days[:2])
        other_stay1.days.set(days[2:4])
        other_stay2.days.set(days[4:6])

        # Force refresh and verify setup
        for stay in [stay_to_delete, other_stay1, other_stay2]:
            stay.refresh_from_db()
            assert stay.days.count() == 2, f"Stay {stay.pk} should have exactly 2 days"

        # Verify trip has exactly 3 stays
        trip_stays = Stay.objects.filter(days__trip=trip).distinct()
        assert trip_stays.count() == 3, f"Expected 3 stays, got {trip_stays.count()}"

        # Get stay deletion page
        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay_to_delete.pk)

        self.response_200(response)

        # Verify response
        other_stays = response.context["other_stays"]
        assert other_stays.count() == 2, (
            f"Expected 2 other stays, got {other_stays.count()}"
        )
        assert set(other_stays) == {other_stay1, other_stay2}, "Wrong stays in context"
        assert response.context["show_dropdown"] is True, "show_dropdown should be True"

    def test_post_with_single_other_stay_auto_reassign(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])
        other_stay.days.set(days[2:])

        with self.login(user):
            response = self.post("trips:stay-delete", pk=other_stay.pk)

        self.response_204(response)
        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == stay

    def test_post_with_manual_stay_selection(self):
        """Test stay deletion when manually selecting a new stay from multiple options"""
        user = self.make_user("user")
        # Create a trip with exactly 6 days
        start_date = datetime.date(2024, 1, 1)  # Use fixed date instead of today
        end_date = start_date + datetime.timedelta(days=5)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)
        days = trip.days.all()

        # Create three stays
        stay_to_delete = StayFactory()
        new_stay = StayFactory()
        other_stay = StayFactory()

        # Assign days to stays
        stay_to_delete.days.set(days[:2])  # First two days
        new_stay.days.set(days[2:4])  # Next two days
        other_stay.days.set(days[4:])  # Remaining days

        # Verify initial setup
        assert Stay.objects.count() == 3

        with self.login(user):
            response = self.post(
                "trips:stay-delete",
                pk=stay_to_delete.pk,
                data={"new_stay": new_stay.pk},
            )

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay deleted successfully"

        # Verify stay was deleted
        assert not Stay.objects.filter(pk=stay_to_delete.pk).exists()

        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == new_stay
