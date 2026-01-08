# test_models.py
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest
from django.conf import settings

from trips.models import Event, Experience, Meal, Stay, Transport

pytestmark = pytest.mark.django_db

mock_geocoder_response = Mock(latlng=(10.0, 20.0))


@pytest.fixture
def mocked_geocoder():
    with patch(
        "trips.models.geocoder.mapbox", return_value=mock_geocoder_response
    ) as mocked_geocoder:
        yield mocked_geocoder


class TestTripModel:
    def test_factory(self, user_factory, trip_factory):
        """Test trip model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")

        assert trip.__str__() == "Test Trip"
        assert trip.author == user

    @pytest.mark.parametrize(
        "start_date, end_date, status",
        [
            (date.today() + timedelta(days=14), date.today() + timedelta(days=17), 1),
            (date.today() + timedelta(days=7), date.today() + timedelta(days=10), 1),
            (date.today() + timedelta(days=4), date.today() + timedelta(days=6), 2),
            (date.today() - timedelta(days=1), date.today() + timedelta(days=1), 3),
            (date.today() - timedelta(days=10), date.today() - timedelta(days=8), 4),
        ],
    )
    def test_status(self, user_factory, trip_factory, start_date, end_date, status):
        user = user_factory()
        trip = trip_factory(
            author=user, title="Test Trip", start_date=start_date, end_date=end_date
        )

        assert trip.status == status

    def test_status_without_dates_given(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(
            author=user, title="Test Trip", start_date=None, end_date=None
        )

        assert trip.status == 1

    def test_archived_trip_bypass_dates_checks(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(
            author=user,
            title="Test Trip",
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=8),
            status=5,
        )

        assert trip.status == 5

    def test_trip_get_image_url_none(self, trip_factory):
        """Test get_image_url property returns None when no image"""
        trip = trip_factory()
        assert trip.get_image_url is None

    def test_trip_get_image_url_with_image(self, trip_factory):
        """Test get_image_url property returns URL when image exists"""
        trip = trip_factory()
        trip.image = "trips/2025/11/test.jpg"
        trip.save()
        assert "/media/trips/2025/11/test.jpg" in trip.get_image_url

    def test_trip_needs_attribution_upload(self, trip_factory):
        """Test needs_attribution returns False for uploaded images"""
        trip = trip_factory()
        trip.image_metadata = {"source": "upload"}
        assert trip.needs_attribution is False

    def test_trip_needs_attribution_unsplash(self, trip_factory):
        """Test needs_attribution returns True for Unsplash images"""
        trip = trip_factory()
        trip.image_metadata = {"source": "unsplash", "photographer": "John Doe"}
        assert trip.needs_attribution is True

    def test_trip_get_attribution_text_upload(self, trip_factory):
        """Test get_attribution_text returns None for uploads"""
        trip = trip_factory()
        trip.image_metadata = {"source": "upload"}
        assert trip.get_attribution_text() is None

    def test_trip_get_attribution_text_unsplash(self, trip_factory):
        """Test get_attribution_text returns formatted text for Unsplash"""
        trip = trip_factory()
        trip.image_metadata = {
            "source": "unsplash",
            "photographer": "John Doe",
            "photo_url": "https://unsplash.com/photos/abc123",
        }
        attribution = trip.get_attribution_text()
        assert "John Doe" in attribution
        assert "Unsplash" in attribution


class TestDayModel:
    def test_factory(self, user_factory, trip_factory):
        """Test day automatically created matches requirements"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            title="Test Trip",
        )

        assert trip.days.all().first().__str__() == "Day 1 [Test Trip]"
        assert trip.days.all().first().number == 1
        assert trip.days.all().first().date == trip.start_date
        assert trip.days.all().count() == 3

    def test_days_deleted_when_trip_dates_updated(self, user_factory, trip_factory):
        """Test correct days are deleted when trip dates updated"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
        )

        assert trip.days.all().first().date == date.today()

        trip.start_date = date.today() + timedelta(days=1)
        trip.save()

        assert trip.days.all().first().date == date.today() + timedelta(days=1)

    def test_next_day_property(self, user_factory, trip_factory):
        """Test next_day property returns correct day"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        days = list(trip.days.all())

        # Test first day returns second day
        assert days[0].next_day == days[1]

        # Test middle day returns last day
        assert days[1].next_day == days[2]

        # Test last day returns None
        assert days[2].next_day is None

        # Test day not in trip returns None
        other_trip = trip_factory()
        other_day = other_trip.days.first()
        other_day.trip = trip  # Change trip reference without adding to trip's days
        assert other_day.next_day is None

        # Test with empty trip
        empty_trip = trip_factory()
        empty_trip.days.all().delete()
        test_day = days[0]
        test_day.trip = empty_trip
        assert test_day.next_day is None

    def test_prev_day_property(self, user_factory, trip_factory):
        """Test prev_day property returns correct day"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        days = list(trip.days.all())

        # Test first day returns None
        assert days[0].prev_day is None

        # Test middle day returns first day
        assert days[1].prev_day == days[0]

        # Test last day returns middle day
        assert days[2].prev_day == days[1]

        # Test day not in trip returns None
        other_trip = trip_factory()
        other_day = other_trip.days.first()
        other_day.trip = trip  # Change trip reference without adding to trip's days
        assert other_day.prev_day is None

        # Test with empty trip
        empty_trip = trip_factory()
        empty_trip.days.all().delete()
        test_day = days[0]
        test_day.trip = empty_trip
        assert test_day.prev_day is None

    def test_days_renumbered_when_trip_dates_updated(self, user_factory, trip_factory):
        """Test days are renumbered correctly when trip start_date is moved earlier"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )

        day1 = trip.days.get(number=1)
        day2 = trip.days.get(number=2)
        day3 = trip.days.get(number=3)

        # Move start date one day earlier
        trip.start_date = date.today() - timedelta(days=1)
        trip.save()

        assert trip.days.count() == 4

        # Check the new day
        new_day = trip.days.get(number=1)
        assert new_day.date == date.today() - timedelta(days=1)

        # Check renumbered days
        day1.refresh_from_db()
        day2.refresh_from_db()
        day3.refresh_from_db()

        assert day1.number == 2
        assert day2.number == 3
        assert day3.number == 4

    def test_days_added_when_trip_dates_extended(self, user_factory, trip_factory):
        """Test days are added correctly when trip end_date is moved later"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        assert trip.days.count() == 3

        # Move end date one day later
        trip.end_date = date.today() + timedelta(days=3)
        trip.save()

        assert trip.days.count() == 4
        last_day = trip.days.order_by("number").last()
        assert last_day.number == 4
        assert last_day.date == date.today() + timedelta(days=3)


class TestLinkModel:
    def test_factory(self, user_factory, trip_factory, link_factory):
        """Test link model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        link = link_factory()

        trip.links.add(link)
        trip.save()

        assert link.__str__() == link.url
        assert trip.links.first() == link


# class TestNoteModel:
#     def test_factory(self, user_factory, event_factory, note_factory):
#         """Test note model factory"""
#         user_factory()
#         note = note_factory()

#         assert note.__str__() == f"{note.content[:35]} ..."


class TestEventModel:
    def test_factory(self, user_factory, trip_factory, event_factory):
        """Test event model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        event = event_factory(day=trip.days.first())

        assert event.__str__() == f"{event.name} ({event.start_time})"
        assert event.day.trip == trip

    @patch("geocoder.mapbox")
    def test_save_updates_coordinates(self, mock_geocoder, user_factory, trip_factory):
        # Setup mock response
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        mock_geocoder.reset_mock()

        event = Event.objects.create(
            day=day,
            name="Test Event",
            start_time="10:00",
            end_time="11:00",
            address="Milan, Italy",
        )

        # Verify the coordinates were set from the mock response
        assert event.latitude == 45.4773
        assert event.longitude == 9.1815
        mock_geocoder.assert_called_once_with(
            "Milan, Italy", access_token=settings.MAPBOX_ACCESS_TOKEN
        )

    @patch("geocoder.mapbox")
    def test_save_does_not_update_coordinates_if_address_unchanged(
        self, mock_geocoder, user_factory, trip_factory
    ):
        # Setup mock response
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        event = Event.objects.create(
            day=day,
            name="Test Event",
            start_time="10:00",
            end_time="11:00",
            address="Milan, Italy",
        )

        # Reset mock before saving again
        mock_geocoder.reset_mock()

        # Save again without changing the address
        event.name = "Updated Event Name"
        event.save()

        # Verify geocoder was not called again
        mock_geocoder.assert_not_called()

    def test_swap_times_with_success(self, user_factory, trip_factory, event_factory):
        """Test successful swapping of event times"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        event1 = event_factory(
            day=day, name="First Event", start_time="09:00", end_time="10:00"
        )
        event2 = event_factory(
            day=day, name="Second Event", start_time="14:00", end_time="15:00"
        )

        # Store original times
        event1_original_start = event1.start_time
        event1_original_end = event1.end_time
        event2_original_start = event2.start_time
        event2_original_end = event2.end_time

        # Perform swap
        event1.swap_times_with(event2)

        # Verify times were swapped
        assert event1.start_time == event2_original_start
        assert event1.end_time == event2_original_end
        assert event2.start_time == event1_original_start
        assert event2.end_time == event1_original_end

    def test_swap_times_with_different_days(
        self, user_factory, trip_factory, event_factory
    ):
        """Test error when swapping events from different days"""
        user = user_factory()
        trip = trip_factory(author=user)
        day1 = trip.days.first()
        day2 = trip.days.last()

        event1 = event_factory(day=day1, start_time="09:00", end_time="10:00")
        event2 = event_factory(day=day2, start_time="14:00", end_time="15:00")

        # Verify ValueError is raised when swapping events from different days
        with pytest.raises(ValueError) as exc:
            event1.swap_times_with(event2)
        assert str(exc.value) == "Can only swap events within the same day"

    def test_event_trip_relationship(self, trip_factory, event_factory):
        """Test that event maintains trip relationship when unpaired from day"""
        trip = trip_factory()
        day = trip.days.first()

        # Create event with day
        event = event_factory(day=day)
        assert event.trip == trip

        # Unpair event from day
        event.day = None
        event.save()

        # Verify trip relationship is maintained
        event.refresh_from_db()
        assert event.trip == trip
        assert event in trip.all_events.all()

    def test_event_trip_assignment_on_day_change(self, trip_factory, event_factory):
        """Test that event's trip updates when day changes"""
        trip1 = trip_factory()
        trip2 = trip_factory()
        day1 = trip1.days.first()
        day2 = trip2.days.first()

        event = event_factory(day=day1)
        assert event.trip == trip1

        # Change event's day
        event.day = day2
        event.save()

        event.refresh_from_db()
        assert event.trip == trip2

    @patch("geocoder.mapbox")
    def test_event_geocoding_on_save(self, mock_geocoder, event_factory):
        mock_geocoder.return_value.latlng = [41.890251, 12.492373]  # Colosseum
        event = event_factory(
            address="Colosseum", city="Roma", latitude=None, longitude=None
        )
        event.save()
        mock_geocoder.assert_called_once_with(
            "Colosseum, Roma", access_token=settings.MAPBOX_ACCESS_TOKEN
        )
        assert event.latitude == 41.890251
        assert event.longitude == 12.492373


class TestTransportModel:
    def test_factory(self, user_factory, trip_factory, transport_factory):
        """Test transport model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        transport = transport_factory(day=trip.days.first(), type=Transport.Type.CAR)

        assert (
            transport.__str__()
            == f"{transport.origin_city} → {transport.destination_city} (Car)"
        )
        assert transport.day.trip == trip
        assert transport.category == Event.Category.TRANSPORT
        assert transport.type == Transport.Type.CAR

    def test_duration_property(self, user_factory, trip_factory, transport_factory):
        """Test that duration property calculates correctly"""
        user = user_factory()
        trip = trip_factory(author=user)
        transport = transport_factory(day=trip.days.first())

        # Factory sets start_time to 10:00 and end_time to 11:00
        from datetime import timedelta

        expected_duration = timedelta(hours=1)
        assert transport.duration == expected_duration

    def test_duration_property_overnight(self, user_factory, trip_factory):
        """Test that duration handles overnight transports"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Overnight Train",
            start_time="23:00",
            end_time="06:00",
            type=Transport.Type.TRAIN,
            origin_city="Roma",
            origin_address="Via Marsala 1",
            origin_latitude=41.9009,
            origin_longitude=12.5028,
            destination_city="Milano",
            destination_address="Piazza Duca d'Aosta",
            destination_latitude=45.4842,
            destination_longitude=9.2040,
        )

        from datetime import timedelta

        expected_duration = timedelta(hours=7)
        assert transport.duration == expected_duration

    def test_booking_fields(self, user_factory, trip_factory):
        """Test that booking fields are saved correctly"""
        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Flight to Paris",
            start_time="10:00",
            end_time="12:00",
            type=Transport.Type.PLANE,
            origin_city="Roma",
            destination_city="Paris",
            company="Air France",
            booking_reference="AF1234",
            ticket_url="https://airfrance.com/booking/123",
            price="150.00",
        )

        assert transport.company == "Air France"
        assert transport.booking_reference == "AF1234"
        assert transport.ticket_url == "https://airfrance.com/booking/123"
        assert str(transport.price) == "150.00"

    def test_coordinates_from_factory(
        self, user_factory, trip_factory, transport_factory
    ):
        """Test that coordinates are set correctly from factory"""
        user = user_factory()
        trip = trip_factory(author=user)
        transport = transport_factory(day=trip.days.first())

        # Factory provides coordinates from PLACES data
        assert transport.origin_latitude is not None
        assert transport.origin_longitude is not None
        assert transport.destination_latitude is not None
        assert transport.destination_longitude is not None

    @patch("geocoder.mapbox")
    def test_geocoding_failure(self, mock_geocoder, user_factory, trip_factory):
        """Test that transport handles geocoding failures gracefully"""
        # Mock geocoder to return None for latlng
        mock_geocoder.return_value.latlng = None

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Transport with failed geocoding",
            start_time="10:00",
            end_time="12:00",
            type=Transport.Type.CAR,
            origin_city="InvalidCity",
            destination_city="AnotherInvalidCity",
        )

        # Coordinates should remain None when geocoding fails
        assert transport.origin_latitude is None
        assert transport.origin_longitude is None
        assert transport.destination_latitude is None
        assert transport.destination_longitude is None

    def test_transport_flight_properties(self, trip_factory):
        """Test flight-specific properties"""
        trip = trip_factory()
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Flight to Paris",
            start_time="10:00",
            end_time="12:00",
            type=Transport.Type.PLANE,
            origin_city="Roma",
            destination_city="Paris",
            type_specific_data={
                "flight_number": "AF1234",
                "gate": "B12",
                "terminal": "2",
                "checked_baggage": 2,
            },
        )

        assert transport.flight_number == "AF1234"
        assert transport.gate == "B12"
        assert transport.terminal == "2"
        assert transport.checked_baggage == 2

    def test_transport_train_properties(self, trip_factory):
        """Test train-specific properties"""
        trip = trip_factory()
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Train to Milano",
            start_time="14:00",
            end_time="16:00",
            type=Transport.Type.TRAIN,
            origin_city="Roma",
            destination_city="Milano",
            type_specific_data={
                "train_number": "FR9612",
                "carriage": "7",
                "seat": "42A",
                "platform": "8",
            },
        )

        assert transport.train_number == "FR9612"
        assert transport.carriage == "7"
        assert transport.seat == "42A"
        assert transport.platform == "8"

    def test_transport_car_properties(self, trip_factory):
        """Test car-specific properties"""
        trip = trip_factory()
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Rental car pickup",
            start_time="09:00",
            end_time="09:30",
            type=Transport.Type.CAR,
            origin_city="Milano",
            destination_city="Milano",
            type_specific_data={
                "is_rental": True,
                "license_plate": "AB123CD",
                "car_type": "Fiat 500",
                "rental_booking_reference": "RENT123456",
            },
        )

        assert transport.is_rental is True
        assert transport.license_plate == "AB123CD"
        assert transport.car_type == "Fiat 500"
        assert transport.rental_booking_reference == "RENT123456"

    def test_transport_company_link_property(self, trip_factory):
        """Test company_link property"""
        trip = trip_factory()
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Bus to airport",
            start_time="08:00",
            end_time="09:00",
            type=Transport.Type.BUS,
            origin_city="Milano",
            destination_city="Malpensa",
            type_specific_data={"company_link": "https://terravision.eu"},
        )

        assert transport.company_link == "https://terravision.eu"

    def test_transport_main_transfer_cannot_have_day(self, trip_factory):
        """Test that Transport with is_main_transfer=True cannot have a day"""
        from django.core.exceptions import ValidationError

        trip = trip_factory()
        day = trip.days.first()

        # Try to create a main transfer with a day assigned
        transport = Transport(
            trip=trip,
            day=day,
            name="Main arrival",
            start_time="10:00",
            end_time="12:00",
            type=Transport.Type.PLANE,
            origin_city="Roma",
            destination_city="Paris",
            is_main_transfer=True,
            direction=Transport.Direction.ARRIVAL,
        )

        with pytest.raises(ValidationError) as exc:
            transport.full_clean()

        assert "day" in exc.value.message_dict

    def test_transport_main_transfer_duplicate_direction(self, trip_factory):
        """Test that Transport cannot have duplicate main transfers for same direction"""
        from django.core.exceptions import ValidationError

        trip = trip_factory()

        # Create first arrival transfer
        Transport.objects.create(
            trip=trip,
            day=None,
            name="First arrival",
            start_time="10:00",
            end_time="12:00",
            type=Transport.Type.PLANE,
            origin_city="Roma",
            destination_city="Paris",
            is_main_transfer=True,
            direction=Transport.Direction.ARRIVAL,
        )

        # Try to create second arrival transfer for same trip
        transport2 = Transport(
            trip=trip,
            day=None,
            name="Second arrival",
            start_time="14:00",
            end_time="16:00",
            type=Transport.Type.TRAIN,
            origin_city="London",
            destination_city="Paris",
            is_main_transfer=True,
            direction=Transport.Direction.ARRIVAL,
        )

        with pytest.raises(ValidationError) as exc:
            transport2.full_clean()

        assert "direction" in exc.value.message_dict


class TestExperienceModel:
    def test_factory(self, user_factory, trip_factory, experience_factory):
        """Test experience model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        experience = experience_factory(
            day=trip.days.first(), type=Experience.Type.MUSEUM
        )

        assert experience.__str__() == f"{experience.name} ({trip.title} - Day 1)"
        assert experience.day.trip == trip
        assert experience.category == Event.Category.EXPERIENCE
        assert experience.type == Experience.Type.MUSEUM


class TestMealModel:
    def test_factory(self, user_factory, trip_factory, meal_factory):
        """Test experience model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        experience = meal_factory(day=trip.days.first(), type=Meal.Type.LUNCH)

        assert experience.__str__() == f"{experience.name} ({trip.title} - Day 1)"
        assert experience.day.trip == trip
        assert experience.category == Event.Category.MEAL
        assert experience.type == Meal.Type.LUNCH


class TestStayModel:
    def test_factory(self, user_factory, trip_factory, stay_factory):
        """Test stay model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        day = trip.days.first()
        stay = stay_factory(name="Grand Hotel", day=day)

        # Associate stay with trip's first day
        day.stay = stay
        day.save()

        assert stay.__str__() == "Grand Hotel - Test Trip"
        assert stay.days.first() == day
        assert stay.days.first().trip == trip

    @patch("geocoder.mapbox")
    def test_save_updates_coordinates(self, mock_geocoder, user_factory, trip_factory):
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        stay = Stay.objects.create(
            name="Grand Hotel Milano",
            check_in="14:00",
            check_out="11:00",
            phone_number="+393334445566",
            address="Via Example 123",
            city="Milan",
        )

        assert stay.latitude == 45.4773
        assert stay.longitude == 9.1815
        mock_geocoder.assert_called_once_with(
            "Via Example 123, Milan", access_token=settings.MAPBOX_ACCESS_TOKEN
        )

    @patch("geocoder.mapbox")
    def test_save_does_not_update_coordinates_if_address_unchanged(
        self, mock_geocoder, user_factory, trip_factory
    ):
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        stay = Stay.objects.create(
            name="Grand Hotel Milano",
            check_in="14:00",
            check_out="11:00",
            phone_number="+393334445566",
            address="Via Example 123",
            city="Milan",
        )

        mock_geocoder.reset_mock()

        stay.name = "Updated Hotel Name"
        stay.save()

        mock_geocoder.assert_not_called()

    def test_update_stay_days_removes_previous_stays(self, trip_factory, stay_factory):
        """Test that assigning multiple days to a new stay removes them from previous stays"""
        # Create a trip with 3 days
        trip = trip_factory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())

        # Create two stays and assign days to first stay
        stay1 = stay_factory()
        stay2 = stay_factory()

        # Associate days with stay1 using Day objects
        for day in days:
            day.stay = stay1
            day.save()

        # Verify initial assignment
        assert stay1.days.count() == 3

        # Now update stay2 to include these days
        # This will trigger the post_save signal on Stay
        for day in days:
            day.stay = stay2
            day.save()

        # Save stay2 to ensure signal is triggered
        stay2.save()

        # Refresh stays from database
        stay1.refresh_from_db()
        stay2.refresh_from_db()

        # Verify days were properly transferred
        assert stay2.days.count() == 3
        assert stay1.days.count() == 0

    def test_stay_str_no_day(self, stay_factory):
        """Test stay __str__ method when it has no associated day."""
        stay = stay_factory(name="Lonely Stay")
        assert str(stay) == "Lonely Stay"

    @patch("geocoder.mapbox")
    def test_save_with_no_geocoder_result(self, mock_geocoder, stay_factory):
        # Setup mock response
        mock_geocoder.return_value.latlng = None

        stay = stay_factory(address="Nowhere", latitude=None, longitude=None)

        # Verify the coordinates were not set
        assert stay.latitude is None
        assert stay.longitude is None

    @patch("geocoder.mapbox")
    def test_stay_geocoding_on_save(self, mock_geocoder, stay_factory):
        mock_geocoder.return_value.latlng = [41.890251, 12.492373]  # Colosseum
        stay = stay_factory(
            address="Colosseum", city="Roma", latitude=None, longitude=None
        )
        stay.save()
        mock_geocoder.assert_called_once_with(
            "Colosseum, Roma", access_token=settings.MAPBOX_ACCESS_TOKEN
        )
        assert stay.latitude == 41.890251
        assert stay.longitude == 12.492373


class TestMainTransferModel:
    def test_main_transfer_factory(self, main_transfer_factory):
        """Test MainTransferFactory creates valid main transfer"""
        transfer = main_transfer_factory()

        assert transfer.trip is not None
        assert transfer.type in [1, 2, 3, 4]  # PLANE, TRAIN, CAR, OTHER
        assert transfer.direction in [1, 2]  # ARRIVAL, DEPARTURE
        assert transfer.origin_name
        assert transfer.destination_name

    def test_main_transfer_has_no_day_field(self, main_transfer_factory):
        """Test that MainTransfer model doesn't have a day field (separate model)"""
        transfer = main_transfer_factory()

        # MainTransfer is a separate model and doesn't have a day field
        assert not hasattr(transfer, "day")

    def test_main_transfer_unique_direction_per_trip(self, main_transfer_factory):
        """Test that only one main transfer per direction allowed per trip"""
        from django.db import IntegrityError

        from trips.models import MainTransfer

        transfer1 = main_transfer_factory(direction=1)  # ARRIVAL
        trip = transfer1.trip

        # Try to create another ARRIVAL transfer for the same trip
        # Should fail due to unique constraint
        with pytest.raises(IntegrityError):
            MainTransfer.objects.create(
                trip=trip,
                type=1,  # PLANE
                direction=1,  # ARRIVAL (duplicate)
                origin_name="Roma",
                destination_name="Paris",
                start_time="14:00",
                end_time="18:00",
            )

    def test_main_transfer_different_directions_allowed(self, main_transfer_factory):
        """Test that arrival and departure transfers can coexist"""
        from trips.models import MainTransfer

        arrival = main_transfer_factory(direction=MainTransfer.Direction.ARRIVAL)
        trip = arrival.trip
        departure = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.DEPARTURE,
        )

        assert arrival.direction == MainTransfer.Direction.ARRIVAL
        assert departure.direction == MainTransfer.Direction.DEPARTURE
        assert trip.main_transfers.count() == 2

    def test_normal_transport_cannot_have_direction(self, trip_factory):
        """Test that non-main transfers cannot have a direction"""
        from django.core.exceptions import ValidationError

        trip = trip_factory()
        day = trip.days.first()

        transport = Transport(
            trip=trip,
            day=day,
            name="City bus",
            start_time="10:00",
            end_time="10:30",
            type=Transport.Type.BUS,
            origin_city="Paris",
            destination_city="Paris",
            is_main_transfer=False,
            direction=Transport.Direction.ARRIVAL,
        )

        with pytest.raises(ValidationError) as exc:
            transport.full_clean()

        assert "direction" in exc.value.message_dict

    def test_main_transfer_requires_direction(self, main_transfer_factory):
        """Test that main transfers must have a direction"""
        from django.core.exceptions import ValidationError

        transport = main_transfer_factory.build(direction=None)

        with pytest.raises(ValidationError) as exc:
            transport.full_clean()

        assert "direction" in exc.value.message_dict

    def test_main_transfer_day_none_validation(
        self, main_transfer_factory, trip_factory
    ):
        """Test that main transfers are separate from daily events (no day field)"""
        from trips.models import MainTransfer

        trip = trip_factory()

        # MainTransfer does not have a 'day' field - it's a separate model
        transfer = main_transfer_factory.build(
            trip=trip,
            direction=MainTransfer.Direction.ARRIVAL,
        )

        # Should pass validation - no day field to validate
        transfer.full_clean()
        assert hasattr(transfer, "trip")
        assert not hasattr(transfer, "day")  # MainTransfer has no day field

    def test_main_transfer_validation_passes(self, main_transfer_factory):
        """Test that main transfer validation passes for valid data"""
        from trips.models import MainTransfer

        # This tests the happy path where no validation errors occur
        transfer = main_transfer_factory(direction=MainTransfer.Direction.ARRIVAL)

        # full_clean should pass without errors
        transfer.full_clean()

        assert transfer.pk is not None
        assert not hasattr(transfer, "day")  # MainTransfer has no day field
        assert transfer.direction == MainTransfer.Direction.ARRIVAL

    def test_main_transfer_type_specific_data_flight(self, main_transfer_factory):
        """Test storing flight-specific data"""
        from trips.models import MainTransfer

        transfer = main_transfer_factory(
            type=MainTransfer.Type.PLANE,
            type_specific_data={
                "flight_number": "AF1234",
                "terminal": "T1",
                "company": "Air France",
                "company_website": "https://airfrance.com",
            },
        )

        assert transfer.flight_number == "AF1234"
        assert transfer.terminal == "T1"
        assert transfer.company == "Air France"
        assert transfer.company_website == "https://airfrance.com"

    def test_main_transfer_type_specific_data_train(self, main_transfer_factory):
        """Test storing train-specific data"""
        from trips.models import MainTransfer

        transfer = main_transfer_factory(
            type=MainTransfer.Type.TRAIN,
            type_specific_data={
                "train_number": "FR9612",
                "carriage": "7",
                "seat": "42A",
                "company": "Trenitalia",
                "company_website": "https://trenitalia.com",
            },
        )

        assert transfer.train_number == "FR9612"
        assert transfer.carriage == "7"
        assert transfer.seat == "42A"
        assert transfer.company == "Trenitalia"
        assert transfer.company_website == "https://trenitalia.com"

    def test_main_transfer_type_specific_data_car(self, main_transfer_factory):
        """Test storing car-specific data"""
        from trips.models import MainTransfer

        transfer = main_transfer_factory(
            type=MainTransfer.Type.CAR,
            type_specific_data={
                "is_rental": True,
                "company": "Hertz",
                "company_website": "https://hertz.com",
            },
        )

        assert transfer.is_rental is True
        assert transfer.company == "Hertz"
        assert transfer.company_website == "https://hertz.com"

    def test_main_transfer_type_specific_data_defaults(self, main_transfer_factory):
        """Test that type_specific_data properties return defaults"""
        from trips.models import MainTransfer

        # Use OTHER type with empty type_specific_data
        transfer = main_transfer_factory(
            type=MainTransfer.Type.OTHER, type_specific_data={}
        )

        # Test default values for all properties
        assert transfer.flight_number == ""
        assert transfer.terminal == ""
        assert transfer.train_number == ""
        assert transfer.carriage == ""
        assert transfer.seat == ""
        assert transfer.is_rental is False
        assert transfer.company == ""
        assert transfer.company_website == ""

    def test_main_transfer_str(self, main_transfer_factory):
        """Test MainTransfer __str__ method"""
        from trips.models import MainTransfer

        # Test arrival transfer
        arrival = main_transfer_factory(
            direction=MainTransfer.Direction.ARRIVAL, type=MainTransfer.Type.PLANE
        )
        str_repr = str(arrival)
        assert arrival.trip.title in str_repr
        assert "Arrival" in str_repr
        assert "Plane" in str_repr

        # Test departure transfer
        departure = main_transfer_factory(
            direction=MainTransfer.Direction.DEPARTURE, type=MainTransfer.Type.TRAIN
        )
        str_repr = str(departure)
        assert departure.trip.title in str_repr
        assert "Departure" in str_repr
        assert "Train" in str_repr

    def test_main_transfer_plane_requires_names(self, trip_factory):
        """Test that plane transfers require origin and destination names"""
        from django.core.exceptions import ValidationError

        from trips.models import MainTransfer

        trip = trip_factory()

        # Test missing origin_name
        transfer = MainTransfer(
            trip=trip,
            type=MainTransfer.Type.PLANE,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="",
            destination_name="Paris CDG",
            start_time="10:00",
            end_time="12:00",
        )

        with pytest.raises(ValidationError) as exc:
            transfer.full_clean()

        assert "origin_name" in exc.value.message_dict

    def test_main_transfer_train_requires_names(self, trip_factory):
        """Test that train transfers require origin and destination names"""
        from django.core.exceptions import ValidationError

        from trips.models import MainTransfer

        trip = trip_factory()

        # Test missing destination_name
        transfer = MainTransfer(
            trip=trip,
            type=MainTransfer.Type.TRAIN,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="Paris Gare du Nord",
            destination_name="",
            start_time="14:00",
            end_time="16:00",
        )

        with pytest.raises(ValidationError) as exc:
            transfer.full_clean()

        assert "destination_name" in exc.value.message_dict

    def test_main_transfer_car_requires_addresses(self, trip_factory):
        """Test that car transfers require origin and destination addresses"""
        from django.core.exceptions import ValidationError

        from trips.models import MainTransfer

        trip = trip_factory()

        # Test missing origin_address
        transfer = MainTransfer(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="",
            destination_name="",
            origin_address="",
            destination_address="Via Roma 123, Milano",
            start_time="10:00",
            end_time="12:00",
        )

        with pytest.raises(ValidationError) as exc:
            transfer.full_clean()

        assert "origin_address" in exc.value.message_dict

    def test_main_transfer_other_requires_addresses(self, trip_factory):
        """Test that other transfers require origin and destination addresses"""
        from django.core.exceptions import ValidationError

        from trips.models import MainTransfer

        trip = trip_factory()

        # Test missing destination_address
        transfer = MainTransfer(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="",
            destination_name="",
            origin_address="Via Roma 123, Milano",
            destination_address="",
            start_time="14:00",
            end_time="16:00",
        )

        with pytest.raises(ValidationError) as exc:
            transfer.full_clean()

        assert "destination_address" in exc.value.message_dict

    @patch("geocoder.mapbox")
    def test_main_transfer_car_geocoding_origin(self, mock_geocoder, trip_factory):
        """Test that car transfers geocode origin_address"""
        from trips.models import MainTransfer

        mock_geocoder.return_value.latlng = [45.4642, 9.1900]  # Milan coords

        trip = trip_factory()

        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="",
            destination_name="",
            origin_address="Piazza Duomo, Milano",
            destination_address="Via Roma 123, Milano",
            destination_latitude=45.4773,
            destination_longitude=9.1815,
            start_time="10:00",
            end_time="12:00",
        )

        # Check that geocoding was called for origin
        assert transfer.origin_latitude == 45.4642
        assert transfer.origin_longitude == 9.1900
        mock_geocoder.assert_called_with(
            "Piazza Duomo, Milano", access_token=settings.MAPBOX_ACCESS_TOKEN
        )

    @patch("geocoder.mapbox")
    def test_main_transfer_other_geocoding_destination(
        self, mock_geocoder, trip_factory
    ):
        """Test that other transfers geocode destination_address"""
        from trips.models import MainTransfer

        mock_geocoder.return_value.latlng = [45.4773, 9.1815]  # Milan coords

        trip = trip_factory()

        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.OTHER,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="",
            destination_name="",
            origin_address="Piazza Duomo, Milano",
            origin_latitude=45.4642,
            origin_longitude=9.1900,
            destination_address="Via Roma 123, Milano",
            start_time="14:00",
            end_time="16:00",
        )

        # Check that geocoding was called for destination
        assert transfer.destination_latitude == 45.4773
        assert transfer.destination_longitude == 9.1815
        mock_geocoder.assert_called_with(
            "Via Roma 123, Milano", access_token=settings.MAPBOX_ACCESS_TOKEN
        )

    @patch("geocoder.mapbox")
    def test_main_transfer_car_geocoding_failure(self, mock_geocoder, trip_factory):
        """Test that car transfers handle geocoding failures gracefully"""
        from trips.models import MainTransfer

        # Mock geocoder to return None for latlng
        mock_geocoder.return_value.latlng = None

        trip = trip_factory()

        transfer = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="",
            destination_name="",
            origin_address="Invalid Address",
            destination_address="Another Invalid Address",
            start_time="10:00",
            end_time="12:00",
        )

        # Coordinates should remain None when geocoding fails
        assert transfer.origin_latitude is None
        assert transfer.origin_longitude is None
        assert transfer.destination_latitude is None
        assert transfer.destination_longitude is None
