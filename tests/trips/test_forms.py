from datetime import date, timedelta
from unittest.mock import patch

import pytest

from tests.trips.factories import (
    ExperienceFactory,
    MainTransferFactory,
    StayFactory,
    TripFactory,
)
from trips.forms import (
    AddNoteToStayForm,
    ExperienceForm,
    LinkForm,
    MealForm,
    NoteForm,
    StayForm,
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
            "destination": "NonExistentPlace",
            "start_date": date.today() + timedelta(days=1),
            "end_date": date.today() + timedelta(days=3),
        }
        form = TripForm(data=data)

        assert not form.is_valid()
        assert "Destination not found" in form.errors["destination"]


class TestLinkForm:
    def test_form(self):
        data = {
            "url": "https://www.google.com",
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


class TestExperienceForm:
    @patch("geocoder.mapbox")
    def test_form(self, mock_geocoder, user_factory, trip_factory):
        """Test that the form saves an experience with estimated_duration"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "Uffizi Gallery",
            "type": 1,
            "address": "Piazzale degli Uffizi, Florence",
            "duration": "60",
        }
        form = ExperienceForm(data=data)

        assert form.is_valid()
        experience = form.save(commit=False)
        assert experience.name == "Uffizi Gallery"
        assert experience.estimated_duration.total_seconds() == 3600

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
        """Test form initialization with existing experience populates duration"""
        from datetime import timedelta

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        experience = experience_factory(
            estimated_duration=timedelta(minutes=90), day=day
        )

        form = ExperienceForm(instance=experience)

        assert form.initial["duration"] == 90

    @patch("geocoder.mapbox")
    def test_save_without_commit(self, mock_geocoder):
        """Test save method with commit=False does not persist"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "Walking Tour",
            "type": 1,
            "address": "Starting Point",
            "duration": "120",
        }
        form = ExperienceForm(data=data)

        assert form.is_valid()
        experience = form.save(commit=False)
        assert experience.estimated_duration.total_seconds() == 7200
        assert not Experience.objects.filter(name="Walking Tour").exists()

    def test_save_with_no_duration(self):
        """Test that duration=0 sets estimated_duration to None"""
        data = {
            "name": "Free wander",
            "type": 5,
            "address": "Somewhere",
            "duration": "0",
        }
        form = ExperienceForm(data=data)
        assert form.is_valid()
        instance = form.save(commit=False)
        assert instance.estimated_duration is None

    def test_save_with_opening_hours(self):
        """Test save method with opening hours data."""
        data = {
            "name": "Test Cafe",
            "type": 1,
            "address": "Someplace",
            "duration": "60",
            "website": "https://example.com",
            "monday_closed": "on",
            "tuesday_open": "09:00",
            "tuesday_close": "17:00",
            "wednesday_open": "10:00",
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
        """Test that the form saves a meal with estimated_duration"""
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        data = {
            "name": "La Pergola",
            "type": 1,
            "address": "Via Alberto Cadlolo, 101, Rome",
            "duration": "60",
        }
        form = MealForm(data=data)

        assert form.is_valid()
        meal = form.save(commit=False)
        assert meal.name == "La Pergola"
        assert meal.estimated_duration.total_seconds() == 3600

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
            "type": 2,
            "address": "Via Stella, 22, Modena",
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
        """Test form initialization with existing meal populates duration"""
        from datetime import timedelta

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()
        meal = meal_factory(estimated_duration=timedelta(minutes=90), day=day)

        form = MealForm(instance=meal)

        assert form.initial["duration"] == 90


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
                "flight_number": "AZ1234",
                "terminal": "T1",
            },
        )

        # Initialize form with instance
        form = FlightMainTransferForm(instance=transfer, trip=trip)

        # Check that fields are populated
        assert form.fields["origin_airport"].initial == "Rome Fiumicino Airport"
        assert form.fields["origin_iata"].initial == "FCO"
        assert form.fields["destination_airport"].initial == "Milan Malpensa Airport"
        assert form.fields["destination_iata"].initial == "MXP"
        assert form.fields["flight_number"].initial == "AZ1234"
        assert form.fields["terminal"].initial == "T1"
        # Removed fields are no longer in the form
        assert "company" not in form.fields
        assert "company_website" not in form.fields
        assert "booking_reference" not in form.fields
        assert "ticket_url" not in form.fields

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
            "flight_number": "AZ1234",
            "terminal": "T1",
        }

        form = FlightMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data["flight_number"] == "AZ1234"
        assert data["terminal"] == "T1"
        assert "company" not in data
        assert "company_website" not in data

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
            "flight_number": "AZ1234",
            "terminal": "",  # Empty
        }

        form = FlightMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data["flight_number"] == "AZ1234"
        assert "terminal" not in data

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

        # Create a train transfer
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
        )

        # Initialize form with instance
        form = TrainMainTransferForm(instance=transfer, trip=trip)

        # Check that station fields are populated
        assert form.fields["origin_station"].initial == "Roma Termini"
        assert form.fields["origin_station_id"].initial == "ROMA"
        assert form.fields["destination_station"].initial == "Milano Centrale"
        assert form.fields["destination_station_id"].initial == "MILANO"
        # Removed fields are no longer in the form
        assert "company" not in form.fields
        assert "carriage" not in form.fields
        assert "seat" not in form.fields
        assert "booking_reference" not in form.fields
        assert "ticket_url" not in form.fields
        # train_number is optional (for viaggiatreno lookup)
        assert "train_number" in form.fields
        assert form.fields["train_number"].initial is None

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
        """Test train form returns empty dict when no train number provided"""
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
        }

        form = TrainMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data == {}

    def test_get_type_specific_data_with_train_number(self):
        """Test train form includes train_number when provided"""
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
            "train_number": "2822",
        }

        form = TrainMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        data = form.get_type_specific_data()
        assert data == {"train_number": "2822"}

    def test_populate_train_number_from_instance(self):
        """Test form populates train_number initial from instance type_specific_data"""
        from trips.forms import TrainMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
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
            type_specific_data={"train_number": "FR9619"},
        )

        form = TrainMainTransferForm(instance=transfer, trip=trip)
        assert form.fields["train_number"].initial == "FR9619"

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
        """Test CarMainTransferForm initializes correctly without rental fields"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form = CarMainTransferForm(trip=trip)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields
        assert "company" not in form.fields
        assert "is_rental" not in form.fields
        assert "booking_reference" not in form.fields
        assert "ticket_url" not in form.fields

    def test_populate_from_existing_instance(self):
        """Test form populates address fields from existing MainTransfer instance"""
        from trips.forms import CarMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=1,
            origin_address="Via Roma 1, Rome",
            destination_address="Via Milano 10, Milan",
            start_time="08:00",
            end_time="12:00",
        )

        form = CarMainTransferForm(instance=transfer, trip=trip)

        assert form.fields["origin_address"].initial == "Via Roma 1, Rome"
        assert form.fields["destination_address"].initial == "Via Milano 10, Milan"

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
        }

        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert transfer.type == MainTransfer.Type.CAR
        assert transfer.origin_address == "Via Roma 1, Rome"
        assert transfer.destination_address == "Via Milano 10, Milan"
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

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

    def test_home_address_with_no_direction_does_not_prefill(self):
        """Test CarMainTransferForm with home_address but no direction skips pre-fill"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form = CarMainTransferForm(trip=trip, home_address="Via Casa 1, Roma")

        # Without direction, neither field should be pre-filled from home_address
        assert form.fields["origin_address"].initial is None
        assert form.fields["destination_address"].initial is None

    def test_start_time_is_optional(self):
        """Car transfer form is valid without start_time"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "origin_address": "Via Roma 1, Rome",
            "destination_address": "Via Milano 10, Milan",
        }
        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid(), form.errors

    def test_end_time_is_optional(self):
        """Car transfer form is valid without end_time"""
        from trips.forms import CarMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "origin_address": "Via Roma 1, Rome",
            "destination_address": "Via Milano 10, Milan",
        }
        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid(), form.errors

    def test_save_without_times(self):
        """Car transfer saves correctly without start_time and end_time"""
        from trips.forms import CarMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "origin_address": "Via Roma 1, Rome",
            "destination_address": "Via Milano 10, Milan",
        }
        form = CarMainTransferForm(form_data, trip=trip)
        assert form.is_valid(), form.errors
        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert transfer.start_time is None
        assert transfer.end_time is None
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_flight_form_still_requires_times(self):
        """Flight transfer form still requires start_time and end_time"""
        from trips.forms import FlightMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "origin_airport": "Rome Fiumicino",
            "destination_airport": "Milan Malpensa",
        }
        form = FlightMainTransferForm(form_data, trip=trip)
        assert not form.is_valid()
        assert "start_time" in form.errors
        assert "end_time" in form.errors


class TestOtherMainTransferForm:
    def test_form_initialization(self):
        """Test OtherMainTransferForm initializes correctly without company fields"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        form = OtherMainTransferForm(trip=trip)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields
        assert "company" not in form.fields
        assert "company_website" not in form.fields

    def test_populate_from_existing_instance(self):
        """Test form populates address fields from existing MainTransfer instance"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=1,
            origin_address="Bus Station Rome",
            destination_address="Bus Station Milan",
            start_time="08:00",
            end_time="14:00",
        )

        form = OtherMainTransferForm(instance=transfer, trip=trip)

        assert form.fields["origin_address"].initial == "Bus Station Rome"
        assert form.fields["destination_address"].initial == "Bus Station Milan"

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
        }

        form = OtherMainTransferForm(form_data, trip=trip)
        assert form.is_valid()

        transfer = form.save(commit=True)
        assert transfer.pk is not None
        assert transfer.type == MainTransfer.Type.OTHER
        assert transfer.origin_address == "Bus Station Rome"
        assert transfer.destination_address == "Bus Station Milan"
        assert MainTransfer.objects.filter(pk=transfer.pk).exists()

    def test_form_initialization_without_autocomplete(self):
        """Test form initializes correctly and accepts autocomplete parameter"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        # OtherMainTransferForm accepts but ignores autocomplete parameter
        form = OtherMainTransferForm(trip=trip, autocomplete=False)

        assert "origin_address" in form.fields
        assert "destination_address" in form.fields

    def test_vehicle_type_field_present(self):
        """OtherMainTransferForm has vehicle_type field"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        form = OtherMainTransferForm(trip=trip)

        assert "vehicle_type" in form.fields

    def test_save_with_vehicle_type_stores_in_type_specific_data(self):
        """vehicle_type is saved in type_specific_data JSON field"""
        from trips.forms import OtherMainTransferForm

        trip = TripFactory()
        form_data = {
            "direction": "1",
            "start_time": "08:00",
            "end_time": "14:00",
            "origin_address": "Port of Genoa",
            "destination_address": "Port of Barcelona",
            "vehicle_type": "Ferry",
        }

        form = OtherMainTransferForm(form_data, trip=trip)
        assert form.is_valid(), form.errors
        transfer = form.save(commit=True)

        assert transfer.type_specific_data.get("vehicle_type") == "Ferry"

    def test_vehicle_type_populated_from_existing_instance(self):
        """Form pre-fills vehicle_type from type_specific_data of existing instance"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=1,
            origin_address="Port of Genoa",
            destination_address="Port of Barcelona",
            start_time="08:00",
            end_time="20:00",
            type_specific_data={"vehicle_type": "Ferry"},
        )

        form = OtherMainTransferForm(instance=transfer, trip=trip)
        assert form.fields["vehicle_type"].initial == "Ferry"

    def test_home_address_ignored_for_other_form(self):
        """OtherMainTransferForm ignores home_address — never pre-fills from it"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        form = OtherMainTransferForm(
            trip=trip,
            home_address="Via Casa 1, Roma",
            initial={"direction": MainTransfer.Direction.ARRIVAL},
        )

        assert form.fields["origin_address"].initial is None
        assert form.fields["destination_address"].initial is None

    def test_departure_not_prefilled_from_arrival(self):
        """Other departure form does NOT pre-fill from arrival transfer"""
        from trips.forms import OtherMainTransferForm
        from trips.models import MainTransfer

        trip = TripFactory()
        MainTransferFactory(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_address="Port of Genoa",
            destination_address="Port of Barcelona",
        )

        form = OtherMainTransferForm(
            trip=trip,
            initial={"direction": MainTransfer.Direction.DEPARTURE},
        )

        assert form.fields["origin_address"].initial is None
        assert not hasattr(form, "prefilled_from_arrival")


class TestMainTransferConnectionForm:
    """Tests for MainTransferConnectionForm"""

    def test_form_creates_instance_with_event(self):
        """Test form creates instance with event when not provided"""
        from trips.forms import MainTransferConnectionForm
        from trips.models import MainTransfer

        trip = TripFactory()
        main_transfer = MainTransferFactory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        event = ExperienceFactory(trip=trip, day=first_day)

        form = MainTransferConnectionForm(
            main_transfer=main_transfer,
            destination=event,
            destination_type="event",
        )

        # Instance should be created in __init__
        assert form.instance is not None
        assert form.instance.main_transfer == main_transfer
        assert form.instance.event == event
        assert form.instance.stay is None

    def test_form_creates_instance_with_stay(self):
        """Test form creates instance with stay when not provided"""
        from trips.forms import MainTransferConnectionForm
        from trips.models import MainTransfer

        trip = TripFactory()
        main_transfer = MainTransferFactory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        stay = StayFactory()
        first_day.stay = stay
        first_day.save()

        form = MainTransferConnectionForm(
            main_transfer=main_transfer,
            destination=stay,
            destination_type="stay",
        )

        # Instance should be created in __init__
        assert form.instance is not None
        assert form.instance.main_transfer == main_transfer
        assert form.instance.stay == stay
        assert form.instance.event is None

    def test_form_preserves_existing_instance(self):
        """Test form preserves instance when already provided"""
        from trips.forms import MainTransferConnectionForm
        from trips.models import MainTransfer, MainTransferConnection

        trip = TripFactory()
        main_transfer = MainTransferFactory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        event = ExperienceFactory(trip=trip, day=first_day)

        # Create existing connection
        existing_connection = MainTransferConnection(
            main_transfer=main_transfer,
            event=event,
            transport_mode="walking",
            notes="Existing note",
        )

        # Pass instance to form
        form = MainTransferConnectionForm(
            instance=existing_connection,
            main_transfer=main_transfer,
            destination=event,
            destination_type="event",
        )

        # Should preserve the existing instance
        assert form.instance == existing_connection
        assert form.instance.notes == "Existing note"
        assert form.instance.transport_mode == "walking"


class TestTransportModeRadioSelectWidget:
    """Tests for TransportModeRadioSelect custom widget"""

    def test_render_produces_radio_inputs(self):
        """Widget renders radio inputs for all transport choices"""
        from trips.models import MainTransferConnection
        from trips.widgets import TransportModeRadioSelect

        widget = TransportModeRadioSelect(
            choices=MainTransferConnection.TransportMode.choices
        )
        html = widget.render("transport_mode", "driving")

        assert 'type="radio"' in html
        assert "driving" in html
        assert "transit" in html
        assert "walking" in html
        assert "bicycling" in html

    def test_render_marks_selected_value(self):
        """Widget marks selected value as checked"""
        from trips.models import MainTransferConnection
        from trips.widgets import TransportModeRadioSelect

        widget = TransportModeRadioSelect(
            choices=MainTransferConnection.TransportMode.choices
        )
        html = widget.render("transport_mode", "transit")

        assert 'checked="checked"' in html

    def test_render_with_no_value(self):
        """Widget renders with None value (defaults to driving)"""
        from trips.models import MainTransferConnection
        from trips.widgets import TransportModeRadioSelect

        widget = TransportModeRadioSelect(
            choices=MainTransferConnection.TransportMode.choices
        )
        html = widget.render("transport_mode", None)

        assert 'type="radio"' in html
