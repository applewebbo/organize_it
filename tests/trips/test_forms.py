from datetime import date, time, timedelta
from unittest.mock import Mock, patch

import pytest
from django.utils.translation import activate

from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.forms import (
    AddNoteToStayForm,
    EventChangeTimesForm,
    ExperienceForm,
    LinkForm,
    MainTransferCombinedForm,
    MainTransferForm,
    MealForm,
    NoteForm,
    StayForm,
    TransportForm,
    TripDateUpdateForm,
    TripForm,
)
from trips.models import Experience

pytestmark = pytest.mark.django_db

mock_geocoder_response = Mock(latlng=(10.0, 20.0))
invalid_mock_geocoder_response = Mock(latlng=None)


@pytest.fixture
def mocked_geocoder():
    with patch(
        "trips.models.geocoder.mapbox", return_value=mock_geocoder_response
    ) as mocked_geocoder:
        yield mocked_geocoder


class TestTripForm:
    @patch("geocoder.mapbox")
    def test_form(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        data = {
            "title": "Test Trip",
            "destination": "Milano",
            "description": "Test Description",
            "start_date": date.today() + timedelta(days=10),
            "end_date": date.today() + timedelta(days=12),
        }
        form = TripForm(data=data)

        assert form.is_valid()

    @patch("geocoder.mapbox")
    def test_end_date_before_start_date(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "start_date": date.today() + timedelta(days=12),
            "end_date": date.today() + timedelta(days=10),
            "destination": "Milano",
        }
        form = TripForm(data=data)

        assert not form.is_valid()
        assert "End date must be after start date" in form.non_field_errors()

    @patch("geocoder.mapbox")
    def test_start_date_before_today(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "start_date": date.today() - timedelta(days=7),
            "end_date": date.today() + timedelta(days=10),
            "destination": "Milano",
        }
        form = TripForm(data=data)

        assert not form.is_valid()
        assert "Start date must be after today" in form.errors["start_date"]

    def test_clean_destination_valid(self, mocker):
        """Test destination validation with valid location"""
        mock_geocoder = mocker.patch("geocoder.mapbox")
        mock_geocoder.return_value.ok = True

        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "destination": "Paris",
            "start_date": date.today() + timedelta(days=1),
            "end_date": date.today() + timedelta(days=3),
        }
        form = TripForm(data=data)

        assert form.is_valid()
        assert form.cleaned_data["destination"] == "Paris"

    def test_clean_destination_invalid(self, mocker):
        """Test destination validation with invalid location"""
        mock_geocoder = mocker.patch("geocoder.mapbox")
        mock_geocoder.return_value.ok = False

        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "destination": "NonExistentPlace",
            "start_date": date.today() + timedelta(days=1),
            "end_date": date.today() + timedelta(days=3),
        }
        form = TripForm(data=data)

        assert not form.is_valid()
        assert "Destination not found" in form.errors["destination"]


class TestTripDateUpdateForm(TestCase):
    def test_form(self):
        data = {
            "start_date": date.today() + timedelta(days=10),
            "end_date": date.today() + timedelta(days=12),
        }
        form = TripDateUpdateForm(data=data)

        assert form.is_valid()

    def test_end_date_before_start_date(self):
        data = {
            "start_date": date.today() + timedelta(days=12),
            "end_date": date.today() + timedelta(days=10),
        }
        form = TripDateUpdateForm(data=data)

        assert not form.is_valid()
        assert "End date must be after start date" in form.non_field_errors()

    def test_date_format(self):
        """
        Test that the TripDateUpdateForm dynamically sets the date format
        based on the current language.
        """
        # Create a Trip instance
        user = self.make_user("user")
        trip = TripFactory(author=user)

        # Test for English (MM/DD/YYYY)
        activate("en")
        form = TripDateUpdateForm(instance=trip)
        assert form.fields["start_date"].widget.format == "%m/%d/%Y"
        assert form.fields["end_date"].widget.format == "%m/%d/%Y"

        # Test for Italian (DD/MM/YYYY)
        activate("it")
        form = TripDateUpdateForm(instance=trip)
        assert form.fields["start_date"].widget.format == "%d/%m/%Y"
        assert form.fields["end_date"].widget.format == "%d/%m/%Y"

        # Test for default (ISO format)
        activate("fr")  # Assume French defaults to ISO
        form = TripDateUpdateForm(instance=trip)
        assert form.fields["start_date"].widget.format == "%Y-%m-%d"
        assert form.fields["end_date"].widget.format == "%Y-%m-%d"


class TestLinkForm:
    def test_form(self):
        data = {
            "url": "https://www.google.com",
            "description": "Test Description",
        }
        form = LinkForm(data=data)

        assert form.is_valid()


class TestNoteForm:
    def test_form(self, user_factory, event_factory):
        """
        Test that the form saves notes to an Event instance.
        """
        user_factory()
        event = event_factory()
        data = {
            "notes": "Test content",
        }
        form = NoteForm(data=data, instance=event)
        assert form.is_valid()
        event = form.save()
        assert event.notes == "Test content"


class TestTransportForm:
    @patch("geocoder.mapbox")
    def test_form(self, mock_geocoder, user_factory, trip_factory):
        """Test that the form saves a transport"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip_factory(author=user)
        data = {
            "type": 1,
            "origin_city": "Milan",
            "origin_address": "Piazza Duomo",
            "destination_city": "Rome",
            "destination_address": "Via del Corso",
            "start_time": "10:00",
            "end_time": "12:00",
            "company": "Trenitalia",
            "booking_reference": "ABC123",
            "price": "45.50",
        }
        form = TransportForm(data=data)

        assert form.is_valid()
        transport = form.save(commit=False)
        assert transport.name == "Milan → Rome"
        assert transport.origin_city == "Milan"
        assert transport.destination_city == "Rome"
        assert transport.company == "Trenitalia"
        assert transport.booking_reference == "ABC123"

    @patch("geocoder.mapbox")
    def test_form_url_assumes_https(self, mock_geocoder):
        """Test that URLs without scheme get https:// prepended"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "type": 1,
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "12:00",
            "website": "example.com",
        }
        form = TransportForm(data=data)

        assert form.is_valid()
        transport = form.save(commit=False)
        assert transport.website == "https://example.com"


class TestExperienceForm:
    @patch("geocoder.mapbox")
    def test_form(self, mock_geocoder, user_factory, trip_factory):
        """Test that the form saves an experience"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "Uffizi Gallery",
            "type": 1,  # MUSEUM
            "address": "Piazzale degli Uffizi, Florence",
            "start_time": "10:00",
            "duration": "60",  # 1 hour
            "url": "https://example.com",
        }
        form = ExperienceForm(data=data)

        assert form.is_valid()
        experience = form.save(commit=False)
        assert experience.name == "Uffizi Gallery"
        assert experience.end_time.strftime("%H:%M") == "11:00"

    @patch("geocoder.mapbox")
    def test_form_url_assumes_https(self, mock_geocoder, user_factory, trip_factory):
        """Test that URLs without scheme get https:// prepended"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        data = {
            "name": "Colosseum",
            "type": 1,
            "address": "Piazza del Colosseo, Rome",
            "start_time": "09:00",
            "duration": "90",
            "website": "example.com",
        }
        form = ExperienceForm(data=data)

        assert form.is_valid()
        experience = form.save(commit=False)
        experience.day = day
        experience.save()
        assert experience.website == "https://example.com"

    def test_init_with_existing_instance(
        self, user_factory, trip_factory, experience_factory
    ):
        """Test form initialization with existing experience instance"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        experience = experience_factory(
            start_time=time(10, 0), end_time=time(11, 30), day=day
        )

        form = ExperienceForm(instance=experience)

        # Check that duration was calculated correctly from start/end time
        assert form.initial["duration"] == 90

    @patch("geocoder.mapbox")
    def test_save_with_duration(self, mock_geocoder):
        """Test save method properly converts duration to end_time"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "Walking Tour",
            "type": 1,
            "address": "Starting Point",
            "start_time": "14:00",
            "duration": "120",
            "url": "https://example.com",
        }
        form = ExperienceForm(data=data)

        assert form.is_valid()
        experience = form.save(commit=False)
        assert experience.end_time.strftime("%H:%M") == "16:00"

    @patch("geocoder.mapbox")
    def test_save_without_commit(self, mock_geocoder):
        """Test save method with commit=False"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "Walking Tour",
            "type": 1,
            "address": "Starting Point",
            "start_time": "14:00",
            "duration": "120",
            "url": "https://example.com",
        }
        form = ExperienceForm(data=data)

        assert form.is_valid()
        experience = form.save(commit=False)
        assert experience.end_time.strftime("%H:%M") == "16:00"
        # Verify that the instance wasn't saved to the database
        assert not Experience.objects.filter(name="Walking Tour").exists()

    def test_save_with_opening_hours(self):
        """Test save method with opening hours data."""
        data = {
            "name": "Test Cafe",
            "type": 1,
            "address": "Someplace",
            "start_time": "10:00",
            "duration": "60",
            "website": "https://example.com",
            "monday_closed": "on",  # closed
            "tuesday_open": "09:00",
            "tuesday_close": "17:00",  # open
            "wednesday_open": "10:00",  # only open
        }
        form = ExperienceForm(data=data)
        assert form.is_valid()
        instance = form.save(commit=False)
        assert "monday" not in instance.opening_hours
        assert "tuesday" in instance.opening_hours
        assert instance.opening_hours["tuesday"]["open"] == "09:00"
        assert instance.opening_hours["tuesday"]["close"] == "17:00"
        assert "wednesday" not in instance.opening_hours


class TestMealForm:
    @patch("geocoder.mapbox")
    def test_form(self, mock_geocoder, user_factory, trip_factory):
        """Test that the form saves a meal"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "La Pergola",
            "type": 1,  # LUNCH
            "address": "Via Alberto Cadlolo, 101, Rome",
            "start_time": "13:00",
            "duration": "60",  # 1 hour
            "url": "https://example.com",
        }
        form = MealForm(data=data)

        assert form.is_valid()
        meal = form.save(commit=False)
        assert meal.name == "La Pergola"
        assert meal.end_time.strftime("%H:%M") == "14:00"

    @patch("geocoder.mapbox")
    def test_form_url_assumes_https(self, mock_geocoder, user_factory, trip_factory):
        """Test that URLs without scheme get https:// prepended"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        data = {
            "name": "Osteria Francescana",
            "type": 2,  # DINNER
            "address": "Via Stella, 22, Modena",
            "start_time": "20:00",
            "duration": "90",
            "website": "example.com",
        }
        form = MealForm(data=data)

        assert form.is_valid()
        meal = form.save(commit=False)
        meal.day = day
        meal.save()
        assert meal.website == "https://example.com"

    def test_init_with_existing_instance(
        self, user_factory, trip_factory, meal_factory
    ):
        """Test form initialization with existing meal instance"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        meal = meal_factory(start_time=time(12, 0), end_time=time(13, 30), day=day)

        form = MealForm(instance=meal)

        # Check that duration was calculated correctly from start/end time
        assert form.initial["duration"] == 90

    @patch("geocoder.mapbox")
    def test_save_with_duration(self, mock_geocoder):
        """Test save method properly converts duration to end_time"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "Quick Lunch",
            "type": 1,
            "address": "Restaurant Address",
            "start_time": "12:00",
            "duration": "30",
            "url": "https://example.com",
        }
        form = MealForm(data=data)

        assert form.is_valid()
        meal = form.save(commit=False)
        assert meal.end_time.strftime("%H:%M") == "12:30"


class TestStayForm:
    @patch("geocoder.mapbox")
    def test_form(self, mock_geocoder, user_factory, trip_factory):
        """Test that the form saves a stay"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        days = trip.days.all()

        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "url": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }
        form = StayForm(trip=trip, data=data)

        assert form.is_valid()
        stay = form.save()
        assert stay.name == "Grand Hotel"
        refreshed_days = trip.days.all()
        assert all(day.stay == stay for day in refreshed_days)

    @patch("geocoder.mapbox")
    def test_form_url_assumes_https(self, mock_geocoder, user_factory, trip_factory):
        """Test that URLs without scheme get https:// prepended"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        days = trip.days.all()

        data = {
            "name": "Luxury Resort",
            "check_in": "15:00",
            "check_out": "10:00",
            "address": "Beach Road 123, Miami",
            "website": "example.com",
            "apply_to_days": [day.pk for day in days],
        }
        form = StayForm(trip=trip, data=data)

        assert form.is_valid()
        stay = form.save()
        assert stay.website == "https://example.com"

    def test_init_with_trip(self, user_factory, trip_factory):
        """Test form initialization with trip instance"""
        user = user_factory()
        trip = trip_factory(author=user)

        form = StayForm(trip=trip)

        assert form.fields["apply_to_days"].queryset.count() == trip.days.count()

    def test_phone_number_validation(self, user_factory, trip_factory):
        """Test phone number validation"""
        user = user_factory()
        trip = trip_factory(author=user)
        days = trip.days.all()

        data = {
            "name": "Hotel Test",
            "address": "Test Address",
            "phone_number": "invalid-phone",
            "apply_to_days": [day.pk for day in days],
        }
        form = StayForm(trip=trip, data=data)

        assert not form.is_valid()
        assert "phone_number" in form.errors


class TestEventChangeTimesForm:
    """Test suite for EventChangeTimesForm"""

    def test_form_valid(self, user_factory, trip_factory, experience_factory):
        """Test that form accepts valid time inputs"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        experience = experience_factory(day=day)

        data = {"start_time": "09:00", "end_time": "10:00"}
        form = EventChangeTimesForm(data=data, instance=experience)

        assert form.is_valid()
        event = form.save()
        assert event.start_time.strftime("%H:%M") == "09:00"
        assert event.end_time.strftime("%H:%M") == "10:00"

    def test_form_invalid_end_time_before_start_time(
        self, user_factory, trip_factory, experience_factory
    ):
        """Test that form rejects end time before start time"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        experience = experience_factory(day=day)

        data = {"start_time": "10:00", "end_time": "09:00"}
        form = EventChangeTimesForm(data=data, instance=experience)

        assert not form.is_valid()
        assert "End time must be after start time" in form.non_field_errors()


class TestAddNoteToStayForm:
    def test_form_valid(self, user_factory, trip_factory, stay_factory):
        """
        Test that the form saves notes to a Stay instance.
        """
        user = user_factory()
        trip_factory(author=user)
        stay = stay_factory()
        data = {
            "notes": "Test note for stay",
        }
        form = AddNoteToStayForm(data=data, instance=stay)
        assert form.is_valid()
        stay = form.save()
        assert stay.notes == "Test note for stay"


class TestEventForm:
    def test_save_commit_false(self, event_factory):
        """Test that save(commit=False) does not save the instance"""
        event = event_factory()
        data = {
            "name": "Test Event",
            "address": "Test Address",
            "start_time": "10:00",
            "duration": "60",
            "type": 1,
            "website": "https://example.com",
        }
        form = ExperienceForm(data=data, instance=event)
        assert form.is_valid()
        instance = form.save(commit=False)
        assert not Experience.objects.filter(pk=instance.pk).exists()

    def test_opening_hours_initial_data(self, event_factory):
        """Test that opening hours are correctly initialized from instance"""
        event = event_factory(
            opening_hours={"monday": {"open": "09:00", "close": "17:00"}}
        )
        form = ExperienceForm(instance=event)
        assert not form.initial["monday_closed"]
        assert form.initial["monday_open"] == "09:00"
        assert form.initial["monday_close"] == "17:00"

    def test_opening_hours_empty_string_initial(self, event_factory):
        """Test that opening hours are correctly initialized when empty string"""
        event = event_factory(opening_hours="")
        form = ExperienceForm(instance=event)
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            assert not form.initial[f"{day}_closed"]

    def test_geocode_htmx_attributes(self):
        """Test that htmx attributes are added for geocoding"""
        form = ExperienceForm(geocode=True, data={"type": 1})
        assert "hx-post" in form.fields["name"].widget.attrs
        assert "hx-post" in form.fields["city"].widget.attrs
        assert "x-ref" in form.fields["address"].widget.attrs

    def test_opening_hours_none_initial(self, event_factory):
        """Test that opening hours are correctly initialized when opening_hours is None."""
        event = event_factory(opening_hours=None)
        form = ExperienceForm(instance=event)
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            assert not form.initial[f"{day}_closed"]

    def test_opening_hours_invalid_data_initial(self, event_factory):
        """Test that opening hours are correctly initialized with invalid data."""
        event = event_factory(opening_hours=[])
        form = ExperienceForm(instance=event)
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            assert form.initial[f"{day}_closed"]


class TestMainTransferForm:
    def test_form_initialization(self):
        """Test MainTransferForm initializes correctly"""
        trip = TripFactory()
        form = MainTransferForm(trip=trip)

        assert "direction" in form.fields
        assert "type" in form.fields
        assert "origin_city" in form.fields
        assert "destination_city" in form.fields

    def test_form_prepopulates_destination(self):
        """Test form prepopulates destination with trip destination"""
        trip = TripFactory(destination="Rome")
        form = MainTransferForm(trip=trip)

        assert form.fields["destination_city"].initial == "Rome"

    def test_form_save_sets_main_transfer_flags(self):
        """Test saving sets is_main_transfer and day=None"""
        trip = TripFactory()
        data = {
            "type": 2,  # PLANE
            "direction": 1,  # ARRIVAL
            "origin_city": "Milan",
            "origin_address": "Via Roma 1",
            "destination_city": "Rome",
            "destination_address": "Via del Corso 10",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferForm(data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=False)
        assert transfer.is_main_transfer is True
        assert transfer.day is None
        assert transfer.category == 1  # TRANSPORT

    def test_form_requires_direction(self):
        """Test direction field is required"""
        trip = TripFactory()
        data = {
            "type": 2,
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferForm(data, trip=trip)
        assert not form.is_valid()
        assert "direction" in form.errors


class TestMainTransferCombinedForm:
    def test_adds_flight_fields_for_plane(self):
        """Test flight-specific fields are added for plane type"""
        trip = TripFactory()
        data = {
            "type": "2",  # PLANE
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferCombinedForm(data, trip=trip)

        assert "specific_flight_number" in form.fields
        assert "specific_gate" in form.fields
        assert "specific_terminal" in form.fields
        assert "specific_checked_baggage" in form.fields

    def test_adds_train_fields_for_train(self):
        """Test train-specific fields are added for train type"""
        trip = TripFactory()
        data = {
            "type": "3",  # TRAIN
            "direction": "2",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferCombinedForm(data, trip=trip)

        assert "specific_train_number" in form.fields
        assert "specific_carriage" in form.fields
        assert "specific_seat" in form.fields
        assert "specific_platform" in form.fields

    def test_adds_car_fields_for_car(self):
        """Test car-specific fields are added for car type"""
        trip = TripFactory()
        data = {
            "type": "1",  # CAR
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferCombinedForm(data, trip=trip)

        assert "specific_is_rental" in form.fields
        assert "specific_license_plate" in form.fields
        assert "specific_car_type" in form.fields
        assert "specific_rental_booking_reference" in form.fields

    def test_saves_type_specific_data(self):
        """Test type-specific data is saved to JSONField"""
        trip = TripFactory()
        data = {
            "type": "2",  # PLANE
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
            "specific_flight_number": "AZ1234",
            "specific_gate": "A12",
            "specific_terminal": "T1",
            "specific_checked_baggage": "2",
        }

        form = MainTransferCombinedForm(data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=False)
        assert transfer.type_specific_data["flight_number"] == "AZ1234"
        assert transfer.type_specific_data["gate"] == "A12"
        assert transfer.type_specific_data["terminal"] == "T1"
        assert transfer.type_specific_data["checked_baggage"] == 2

    def test_ignores_empty_specific_fields(self):
        """Test empty specific fields are not saved"""
        trip = TripFactory()
        data = {
            "type": "2",
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
            "specific_flight_number": "AZ1234",
            "specific_gate": "",  # Empty
            "specific_terminal": "",  # Empty
        }

        form = MainTransferCombinedForm(data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=False)
        assert "flight_number" in transfer.type_specific_data
        assert "gate" not in transfer.type_specific_data
        assert "terminal" not in transfer.type_specific_data

    def test_edit_with_existing_data(self):
        """Test editing transfer with existing type-specific data"""
        trip = TripFactory()
        from trips.models import Transport

        # Create a transfer with existing data
        transfer = Transport.objects.create(
            trip=trip,
            type=2,  # PLANE
            direction=1,
            is_main_transfer=True,
            origin_city="Milan",
            destination_city="Rome",
            start_time="10:00",
            end_time="11:30",
            type_specific_data={
                "flight_number": "AZ1234",
                "gate": "A12",
                "terminal": "T1",
            },
        )

        # Edit the transfer
        data = {
            "type": "2",
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
            "specific_flight_number": "AZ5678",  # Changed
            "specific_gate": "B5",  # Changed
        }

        form = MainTransferCombinedForm(data, instance=transfer, trip=trip)
        assert form.is_valid()

        # Check that initial values were populated
        assert "specific_flight_number" in form.fields
        assert form.fields["specific_flight_number"].initial == "AZ1234"

        # Save and verify updated data
        updated_transfer = form.save(commit=False)
        assert updated_transfer.type_specific_data["flight_number"] == "AZ5678"
        assert updated_transfer.type_specific_data["gate"] == "B5"

    def test_save_with_commit_true(self):
        """Test saving with commit=True actually saves to database"""
        trip = TripFactory()
        data = {
            "type": "2",
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferForm(data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None  # Saved to database

        from trips.models import Transport

        assert Transport.objects.filter(pk=transfer.pk).exists()

    def test_edit_train_with_existing_data(self):
        """Test editing train transfer with existing type-specific data"""
        trip = TripFactory()
        from trips.models import Transport

        # Create a train transfer with existing data
        transfer = Transport.objects.create(
            trip=trip,
            type=3,  # TRAIN
            direction=1,
            is_main_transfer=True,
            origin_city="Milan",
            destination_city="Rome",
            start_time="10:00",
            end_time="14:00",
            type_specific_data={
                "train_number": "FR9612",
                "carriage": "7",
                "seat": "42A",
            },
        )

        # Edit the transfer
        data = {
            "type": "3",
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "14:00",
            "specific_train_number": "IC1234",  # Changed
        }

        form = MainTransferCombinedForm(data, instance=transfer, trip=trip)
        assert form.is_valid()
        updated_transfer = form.save(commit=False)
        assert updated_transfer.type_specific_data["train_number"] == "IC1234"

    def test_edit_car_with_existing_data(self):
        """Test editing car transfer with existing type-specific data"""
        trip = TripFactory()
        from trips.models import Transport

        # Create a car transfer with existing data
        transfer = Transport.objects.create(
            trip=trip,
            type=1,  # CAR
            direction=2,
            is_main_transfer=True,
            origin_city="Rome",
            destination_city="Milan",
            start_time="08:00",
            end_time="12:00",
            type_specific_data={
                "license_plate": "AB123CD",
                "car_type": "Sedan",
            },
        )

        # Edit the transfer
        data = {
            "type": "1",
            "direction": "2",
            "origin_city": "Rome",
            "destination_city": "Milan",
            "start_time": "08:00",
            "end_time": "12:00",
            "specific_license_plate": "XY789ZW",  # Changed
        }

        form = MainTransferCombinedForm(data, instance=transfer, trip=trip)
        assert form.is_valid()
        updated_transfer = form.save(commit=False)
        assert updated_transfer.type_specific_data["license_plate"] == "XY789ZW"

    def test_no_specific_fields_for_other_transport(self):
        """Test no specific fields added for BUS/BOAT/TAXI/OTHER"""
        trip = TripFactory()

        # Test with BUS type (5)
        data = {
            "type": "5",  # BUS - no specific fields
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "14:00",
        }

        form = MainTransferCombinedForm(data, trip=trip)

        # No specific fields should be added
        assert "specific_flight_number" not in form.fields
        assert "specific_train_number" not in form.fields
        assert "specific_license_plate" not in form.fields

        # Also test with no data (GET request) - transport_type will be None
        form_empty = MainTransferCombinedForm(trip=trip)
        assert "specific_flight_number" not in form_empty.fields

        # Test with invalid type that doesn't match any condition
        data_invalid_type = {
            "type": "99",  # Invalid type
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "14:00",
        }
        form_invalid = MainTransferCombinedForm(data_invalid_type, trip=trip)
        assert "specific_flight_number" not in form_invalid.fields

        # Test with empty type in POST data
        data_empty_type = {
            "type": "",  # Empty string - will fail the "if transport_type:" check
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "14:00",
        }
        form_empty_type = MainTransferCombinedForm(data_empty_type, trip=trip)
        assert "specific_flight_number" not in form_empty_type.fields
