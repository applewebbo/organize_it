from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from django.utils.translation import activate

from tests.test import TestCase
from tests.trips.factories import MainTransferFactory, TripFactory
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

    def test_form_save_with_commit_true(self):
        """Test MainTransferForm save with commit=True"""
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

        transfer = form.save(commit=True)
        assert transfer.pk is not None  # Saved to DB
        from trips.models import Transport

        assert Transport.objects.filter(pk=transfer.pk).exists()


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

    def test_reads_transport_type_from_instance(self):
        """Test reading transport type from instance to add type-specific fields"""
        trip = TripFactory()
        from trips.models import Transport

        # Create a plane transfer
        transfer = Transport.objects.create(
            trip=trip,
            type=2,  # PLANE
            direction=1,
            is_main_transfer=True,
            origin_city="Milan",
            destination_city="Rome",
            start_time="10:00",
            end_time="11:30",
        )

        # Initialize form with instance (without POST data)
        form = MainTransferCombinedForm(instance=transfer, trip=trip)

        # Should add flight-specific fields based on instance.type
        assert "specific_flight_number" in form.fields
        assert "specific_gate" in form.fields

    def test_combined_form_save_with_commit_true(self):
        """Test MainTransferCombinedForm save with commit=True"""
        trip = TripFactory()
        data = {
            "type": "2",
            "direction": "1",
            "origin_city": "Milan",
            "destination_city": "Rome",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferCombinedForm(data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        from trips.models import Transport

        assert Transport.objects.filter(pk=transfer.pk).exists()


class TestMainTransferBaseForm:
    def test_save_with_commit_false(self):
        """Test MainTransferBaseForm save with commit=False"""
        from trips.forms import MainTransferBaseForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferBaseForm(form_data, trip=trip)
        assert form.is_valid()

        instance = form.save(commit=False)
        assert instance.trip == trip
        assert not instance.pk  # Not saved to DB

    def test_get_type_specific_data_default(self):
        """Test get_type_specific_data returns empty dict by default"""
        from trips.forms import MainTransferBaseForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "11:30",
        }

        form = MainTransferBaseForm(form_data, trip=trip)
        assert form.is_valid()
        assert form.get_type_specific_data() == {}


class TestFlightMainTransferForm:
    def test_populate_from_existing_instance(self):
        """Test form populates fields from existing MainTransfer instance"""
        from trips.forms import FlightMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create a flight transfer with type-specific data
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=1,
            origin_code="FCO",
            origin_name="Rome Fiumicino Airport",
            destination_code="MXP",
            destination_name="Milan Malpensa Airport",
            start_time="10:00",
            end_time="11:30",
            type_specific_data={
                "company": "Alitalia",
                "flight_number": "AZ1234",
                "terminal": "T1",
                "company_website": "https://alitalia.com",
            },
        )

        # Initialize form with instance
        form = FlightMainTransferForm(instance=transfer, trip=trip)

        # Check that fields are populated
        assert form.fields["origin_airport"].initial == "Rome Fiumicino Airport"
        assert form.fields["origin_iata"].initial == "FCO"
        assert form.fields["destination_airport"].initial == "Milan Malpensa Airport"
        assert form.fields["destination_iata"].initial == "MXP"
        assert form.fields["company"].initial == "Alitalia"
        assert form.fields["flight_number"].initial == "AZ1234"
        assert form.fields["terminal"].initial == "T1"
        assert form.fields["company_website"].initial == "https://alitalia.com"

    def test_save_with_coordinates(self):
        """Test save method with coordinate data"""
        from trips.forms import FlightMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "11:30",
            "origin_airport": "Rome Fiumicino",
            "origin_iata": "FCO",
            "origin_latitude": "41.8003",
            "origin_longitude": "12.2389",
            "destination_airport": "Milan Malpensa",
            "destination_iata": "MXP",
            "destination_latitude": "45.6301",
            "destination_longitude": "8.7281",
        }

        form = FlightMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=False)
        assert transfer.origin_latitude == 41.8003
        assert transfer.origin_longitude == 12.2389
        assert transfer.destination_latitude == 45.6301
        assert transfer.destination_longitude == 8.7281

    def test_get_type_specific_data(self):
        """Test flight-specific data is extracted correctly"""
        from trips.forms import FlightMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "11:30",
            "origin_airport": "Rome",
            "origin_iata": "FCO",
            "destination_airport": "Milan",
            "destination_iata": "MXP",
            "company": "Alitalia",
            "flight_number": "AZ1234",
            "terminal": "T1",
            "company_website": "https://alitalia.com",
        }

        form = FlightMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data["company"] == "Alitalia"
        assert data["flight_number"] == "AZ1234"
        assert data["terminal"] == "T1"
        assert data["company_website"] == "https://alitalia.com"

    def test_get_type_specific_data_with_empty_fields(self):
        """Test flight-specific data excludes empty fields"""
        from trips.forms import FlightMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "11:30",
            "origin_airport": "Rome",
            "origin_iata": "FCO",
            "destination_airport": "Milan",
            "destination_iata": "MXP",
            "company": "",  # Empty
            "flight_number": "AZ1234",
            "terminal": "",  # Empty
            "company_website": "",  # Empty
        }

        form = FlightMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert "company" not in data
        assert data["flight_number"] == "AZ1234"
        assert "terminal" not in data
        assert "company_website" not in data

    def test_save_with_commit_true(self):
        """Test FlightMainTransferForm save with commit=True"""
        from trips.forms import FlightMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "11:30",
            "origin_airport": "Rome",
            "origin_iata": "FCO",
            "destination_airport": "Milan",
            "destination_iata": "MXP",
        }

        form = FlightMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_departure_prefilled_from_arrival_when_types_match(self):
        """Test departure form pre-fills from arrival when transport types match"""
        from trips.forms import FlightMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create arrival transfer using factory
        MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Rome FCO",
            origin_code="FCO",
            origin_latitude=41.8002,
            origin_longitude=12.2389,
            destination_name="Barcelona BCN",
            destination_code="BCN",
            destination_latitude=41.2971,
            destination_longitude=2.0833,
        )

        # Create new departure form
        form = FlightMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are inverted
        assert form.fields["origin_airport"].initial == "Barcelona BCN"
        assert form.fields["origin_iata"].initial == "BCN"
        assert form.fields["origin_latitude"].initial == 41.2971
        assert form.fields["origin_longitude"].initial == 2.0833
        assert form.fields["destination_airport"].initial == "Rome FCO"
        assert form.fields["destination_iata"].initial == "FCO"
        assert form.fields["destination_latitude"].initial == 41.8002
        assert form.fields["destination_longitude"].initial == 12.2389
        assert form.prefilled_from_arrival is True

    def test_departure_not_prefilled_when_no_arrival(self):
        """Test departure NOT pre-filled when no arrival exists"""
        from trips.forms import FlightMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create new departure form without arrival
        form = FlightMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are NOT pre-filled
        assert form.fields["origin_airport"].initial is None
        assert not hasattr(form, "prefilled_from_arrival")

    def test_departure_not_prefilled_when_editing_existing(self):
        """Test existing departure NOT overwritten by arrival data"""
        from trips.forms import FlightMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create arrival transfer
        MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Rome FCO",
            origin_code="FCO",
            destination_name="Barcelona BCN",
            destination_code="BCN",
        )

        # Create existing departure transfer
        existing_departure = MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="Madrid MAD",
            origin_code="MAD",
            destination_name="Paris CDG",
            destination_code="CDG",
        )

        # Edit form for existing departure
        form = FlightMainTransferForm(
            instance=existing_departure,
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Should NOT be overwritten - should use existing data
        assert form.fields["origin_airport"].initial == "Madrid MAD"
        assert form.fields["origin_iata"].initial == "MAD"
        assert not hasattr(form, "prefilled_from_arrival")


class TestTrainMainTransferForm:
    def test_populate_from_existing_instance(self):
        """Test form populates fields from existing MainTransfer instance"""
        from trips.forms import TrainMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create a train transfer with type-specific data
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.TRAIN,
            direction=1,
            origin_code="ROMA",
            origin_name="Roma Termini",
            destination_code="MILANO",
            destination_name="Milano Centrale",
            start_time="10:00",
            end_time="13:30",
            type_specific_data={
                "company": "Trenitalia",
                "train_number": "FR9612",
                "carriage": "7",
                "seat": "42A",
                "company_website": "https://trenitalia.com",
            },
        )

        # Initialize form with instance
        form = TrainMainTransferForm(instance=transfer, trip=trip)

        # Check that fields are populated
        assert form.fields["origin_station"].initial == "Roma Termini"
        assert form.fields["origin_station_id"].initial == "ROMA"
        assert form.fields["destination_station"].initial == "Milano Centrale"
        assert form.fields["destination_station_id"].initial == "MILANO"
        assert form.fields["company"].initial == "Trenitalia"
        assert form.fields["train_number"].initial == "FR9612"
        assert form.fields["carriage"].initial == "7"
        assert form.fields["seat"].initial == "42A"
        assert form.fields["company_website"].initial == "https://trenitalia.com"

    def test_save_with_coordinates(self):
        """Test save method with coordinate data"""
        from trips.forms import TrainMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "13:30",
            "origin_station": "Roma Termini",
            "origin_station_id": "ROMA",
            "origin_latitude": "41.9009",
            "origin_longitude": "12.5030",
            "destination_station": "Milano Centrale",
            "destination_station_id": "MILANO",
            "destination_latitude": "45.4871",
            "destination_longitude": "9.2050",
        }

        form = TrainMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=False)
        assert transfer.origin_latitude == 41.9009
        assert transfer.origin_longitude == 12.5030
        assert transfer.destination_latitude == 45.4871
        assert transfer.destination_longitude == 9.2050

    def test_get_type_specific_data(self):
        """Test train-specific data is extracted correctly"""
        from trips.forms import TrainMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "13:30",
            "origin_station": "Roma Termini",
            "origin_station_id": "ROMA",
            "destination_station": "Milano Centrale",
            "destination_station_id": "MILANO",
            "company": "Trenitalia",
            "train_number": "FR9612",
            "carriage": "7",
            "seat": "42A",
            "company_website": "https://trenitalia.com",
        }

        form = TrainMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data["company"] == "Trenitalia"
        assert data["train_number"] == "FR9612"
        assert data["carriage"] == "7"
        assert data["seat"] == "42A"
        assert data["company_website"] == "https://trenitalia.com"

    def test_get_type_specific_data_with_empty_fields(self):
        """Test train-specific data excludes empty fields"""
        from trips.forms import TrainMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "13:30",
            "origin_station": "Roma Termini",
            "origin_station_id": "ROMA",
            "destination_station": "Milano Centrale",
            "destination_station_id": "MILANO",
            "company": "",  # Empty
            "train_number": "FR9612",
            "carriage": "",  # Empty
            "seat": "",  # Empty
            "company_website": "",  # Empty
        }

        form = TrainMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert "company" not in data
        assert data["train_number"] == "FR9612"
        assert "carriage" not in data
        assert "seat" not in data
        assert "company_website" not in data

    def test_save_with_commit_true(self):
        """Test TrainMainTransferForm save with commit=True"""
        from trips.forms import TrainMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "10:00",
            "end_time": "13:30",
            "origin_station": "Roma Termini",
            "origin_station_id": "ROMA",
            "destination_station": "Milano Centrale",
            "destination_station_id": "MILANO",
        }

        form = TrainMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_form_initialization_without_autocomplete(self):
        """Test form initializes without autocomplete"""
        from trips.forms import TrainMainTransferForm

        trip = TripFactory()
        form = TrainMainTransferForm(trip=trip, autocomplete=False)

        # Fields should exist but without hx-post attributes
        assert "origin_station" in form.fields
        assert "destination_station" in form.fields
        # No HTMX attributes when autocomplete=False
        assert "hx-post" not in form.fields["origin_station"].widget.attrs

    def test_departure_prefilled_from_arrival_when_types_match(self):
        """Test departure form pre-fills from arrival for train"""
        from trips.forms import TrainMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create arrival transfer
        MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.TRAIN,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Roma Termini",
            origin_code="ROMA",
            origin_latitude=41.9009,
            origin_longitude=12.5028,
            destination_name="Milano Centrale",
            destination_code="MILANO",
            destination_latitude=45.4869,
            destination_longitude=9.2044,
        )

        # Create new departure form
        form = TrainMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are inverted
        assert form.fields["origin_station"].initial == "Milano Centrale"
        assert form.fields["origin_station_id"].initial == "MILANO"
        assert form.fields["destination_station"].initial == "Roma Termini"
        assert form.fields["destination_station_id"].initial == "ROMA"
        assert form.prefilled_from_arrival is True


class TestCarMainTransferForm:
    def test_form_initialization(self):
        """Test CarMainTransferForm initializes correctly"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form = CarMainTransferForm(trip=trip)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields
        assert "company" in form.fields
        assert "is_rental" in form.fields

    def test_populate_from_existing_instance(self):
        """Test form populates fields from existing MainTransfer instance"""
        from trips.forms import CarMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create a car transfer with type-specific data
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=1,
            origin_address="Via Roma 1, Rome",
            destination_address="Via Milano 10, Milan",
            start_time="08:00",
            end_time="12:00",
            type_specific_data={
                "company": "Hertz",
                "is_rental": True,
                "company_website": "https://hertz.com",
            },
        )

        # Initialize form with instance
        form = CarMainTransferForm(instance=transfer, trip=trip)

        # Check that fields are populated
        assert form.fields["origin_address"].initial == "Via Roma 1, Rome"
        assert form.fields["destination_address"].initial == "Via Milano 10, Milan"
        assert form.fields["company"].initial == "Hertz"
        assert form.fields["is_rental"].initial is True
        assert form.fields["company_website"].initial == "https://hertz.com"

    def test_save_creates_car_transfer(self):
        """Test save method creates car transfer correctly"""
        from trips.forms import CarMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "12:00",
            "origin_address": "Via Roma 1, Rome",
            "destination_address": "Via Milano 10, Milan",
            "company": "Hertz",
            "is_rental": True,
            "company_website": "https://hertz.com",
        }

        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert transfer.type == MainTransfer.Type.CAR
        assert transfer.origin_address == "Via Roma 1, Rome"
        assert transfer.destination_address == "Via Milano 10, Milan"
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_get_type_specific_data(self):
        """Test car-specific data is extracted correctly"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "12:00",
            "origin_address": "Via Roma 1",
            "destination_address": "Via Milano 10",
            "company": "Hertz",
            "is_rental": True,
            "company_website": "https://hertz.com",
        }

        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data["company"] == "Hertz"
        assert data["is_rental"] is True
        assert data["company_website"] == "https://hertz.com"

    def test_get_type_specific_data_with_empty_fields(self):
        """Test car-specific data excludes empty fields"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "12:00",
            "origin_address": "Via Roma 1",
            "destination_address": "Via Milano 10",
            "company": "",  # Empty
            "is_rental": False,  # False (not True)
            "company_website": "",  # Empty
        }

        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert "company" not in data
        assert "is_rental" not in data  # False is not included
        assert "company_website" not in data

    def test_form_initialization_without_autocomplete(self):
        """Test form initializes correctly and accepts autocomplete parameter"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        # CarMainTransferForm accepts but ignores autocomplete parameter
        form = CarMainTransferForm(trip=trip, autocomplete=False)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields

    def test_departure_prefilled_from_arrival_when_types_match(self):
        """Test departure form pre-fills from arrival for car"""
        from trips.forms import CarMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create arrival transfer
        MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_address="Via Roma 1, Milano",
            destination_address="Piazza Duomo 10, Firenze",
        )

        # Create new departure form
        form = CarMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are inverted
        assert form.fields["origin_address"].initial == "Piazza Duomo 10, Firenze"
        assert form.fields["destination_address"].initial == "Via Roma 1, Milano"
        assert form.prefilled_from_arrival is True

    def test_departure_not_prefilled_when_no_arrival(self):
        """Test departure NOT pre-filled when no arrival exists for car"""
        from trips.forms import CarMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create new departure form without arrival
        form = CarMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are NOT pre-filled
        assert form.fields["origin_address"].initial is None
        assert not hasattr(form, "prefilled_from_arrival")


class TestOtherMainTransferForm:
    def test_form_initialization(self):
        """Test OtherMainTransferForm initializes correctly"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        form = OtherMainTransferForm(trip=trip)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields
        assert "company" in form.fields

    def test_populate_from_existing_instance(self):
        """Test form populates fields from existing MainTransfer instance"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create an other transfer with type-specific data
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=1,
            origin_address="Bus Station Rome",
            destination_address="Bus Station Milan",
            start_time="08:00",
            end_time="14:00",
            type_specific_data={
                "company": "FlixBus",
                "company_website": "https://flixbus.com",
            },
        )

        # Initialize form with instance
        form = OtherMainTransferForm(instance=transfer, trip=trip)

        # Check that fields are populated
        assert form.fields["origin_address"].initial == "Bus Station Rome"
        assert form.fields["destination_address"].initial == "Bus Station Milan"
        assert form.fields["company"].initial == "FlixBus"
        assert form.fields["company_website"].initial == "https://flixbus.com"

    def test_save_creates_other_transfer(self):
        """Test save method creates other transfer correctly"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "14:00",
            "origin_address": "Bus Station Rome",
            "destination_address": "Bus Station Milan",
            "company": "FlixBus",
            "company_website": "https://flixbus.com",
        }

        form = OtherMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert transfer.type == MainTransfer.Type.OTHER
        assert transfer.origin_address == "Bus Station Rome"
        assert transfer.destination_address == "Bus Station Milan"
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_get_type_specific_data(self):
        """Test generic transfer specific data is extracted correctly"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "14:00",
            "origin_address": "Bus Station",
            "destination_address": "Train Station",
            "company": "FlixBus",
            "company_website": "https://flixbus.com",
        }

        form = OtherMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data["company"] == "FlixBus"
        assert data["company_website"] == "https://flixbus.com"

    def test_get_type_specific_data_with_empty_fields(self):
        """Test generic transfer specific data excludes empty fields"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "14:00",
            "origin_address": "Bus Station",
            "destination_address": "Train Station",
            "company": "",  # Empty
            "company_website": "",  # Empty
        }

        form = OtherMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert "company" not in data
        assert "company_website" not in data

    def test_form_initialization_without_autocomplete(self):
        """Test form initializes correctly and accepts autocomplete parameter"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        # OtherMainTransferForm accepts but ignores autocomplete parameter
        form = OtherMainTransferForm(trip=trip, autocomplete=False)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields

    def test_departure_prefilled_from_arrival_when_types_match(self):
        """Test departure form pre-fills from arrival for other transport"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create arrival transfer
        MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_address="Port of Genoa",
            destination_address="Port of Barcelona",
        )

        # Create new departure form
        form = OtherMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are inverted
        assert form.fields["origin_address"].initial == "Port of Barcelona"
        assert form.fields["destination_address"].initial == "Port of Genoa"
        assert form.prefilled_from_arrival is True

    def test_departure_not_prefilled_when_no_arrival(self):
        """Test departure NOT pre-filled when no arrival exists for other"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()

        # Create new departure form without arrival
        form = OtherMainTransferForm(
            trip=trip,
            autocomplete=False,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        # Check fields are NOT pre-filled
        assert form.fields["origin_address"].initial is None
        assert not hasattr(form, "prefilled_from_arrival")
