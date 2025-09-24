# test_models.py
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

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


class TestTransportModel:
    def test_factory(self, user_factory, trip_factory, transport_factory):
        """Test transport model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        transport = transport_factory(day=trip.days.first(), type=Transport.Type.CAR)

        assert transport.__str__() == f"{transport.name} ({trip.title} - Day 1)"
        assert transport.day.trip == trip
        assert transport.category == Event.Category.TRANSPORT
        assert transport.type == Transport.Type.CAR

    @patch("geocoder.mapbox")
    def test_save_updates_coordinates(self, mock_geocoder, user_factory, trip_factory):
        # Setup mock response
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        mock_geocoder.reset_mock()

        transport = Transport.objects.create(
            day=day,
            name="Train to Milan",
            start_time="10:00",
            end_time="11:00",
            type=Transport.Type.TRAIN,
            destination="Milan, Italy",
        )

        # Verify the coordinates were set from the mock response
        assert transport.dest_latitude == 45.4773
        assert transport.dest_longitude == 9.1815
        assert mock_geocoder.call_count == 2

    @patch("geocoder.mapbox")
    def test_save_does_not_update_coordinates_if_destination_unchanged(
        self, mock_geocoder, user_factory, trip_factory
    ):
        # Setup mock response
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Train to Milan",
            start_time="10:00",
            end_time="11:00",
            type=Transport.Type.TRAIN,
            destination="Milan, Italy",
        )

        # Reset mock before saving again
        mock_geocoder.reset_mock()

        # Save again without changing the destination
        transport.name = "Updated Transport Name"
        transport.save()

        # Verify geocoder was not called again
        mock_geocoder.assert_not_called()

    @patch("geocoder.mapbox")
    def test_save_updates_coordinates_if_destination_changed(
        self, mock_geocoder, user_factory, trip_factory
    ):
        # Setup mock response
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Train to Milan",
            start_time="10:00",
            end_time="11:00",
            type=Transport.Type.TRAIN,
            destination="Milan, Italy",
        )

        # Reset mock before saving again
        mock_geocoder.reset_mock()
        mock_geocoder.return_value.latlng = [48.8566, 2.3522]

        # Save again with changed destination
        transport.destination = "Paris, France"
        transport.save()

        # Verify geocoder was called again
        mock_geocoder.assert_called_with(
            "Paris, France", access_token=settings.MAPBOX_ACCESS_TOKEN
        )
        transport.refresh_from_db()
        assert transport.dest_latitude == 48.8566
        assert transport.dest_longitude == 2.3522

    @patch("geocoder.mapbox")
    def test_save_with_no_geocoder_result(
        self, mock_geocoder, user_factory, trip_factory
    ):
        # Setup mock response
        mock_geocoder.return_value.latlng = None

        user = user_factory()
        trip = trip_factory(author=user)
        day = trip.days.first()

        transport = Transport.objects.create(
            day=day,
            name="Train to Nowhere",
            start_time="10:00",
            end_time="11:00",
            type=Transport.Type.TRAIN,
            destination="Nowhere",
        )

        # Verify the coordinates were not set
        assert transport.dest_latitude is None
        assert transport.dest_longitude is None


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
        stay = stay_factory(name="Grand Hotel")

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
            address="Via Example 123, Milan, Italy",
        )

        assert stay.latitude == 45.4773
        assert stay.longitude == 9.1815
        mock_geocoder.assert_called_once_with(
            "Via Example 123, Milan, Italy", access_token=settings.MAPBOX_ACCESS_TOKEN
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
            address="Via Example 123, Milan, Italy",
        )

        mock_geocoder.reset_mock()

        stay.name = "Updated Hotel Name"
        stay.save()

        mock_geocoder.assert_not_called()

    def test_phone_number_validation(self, stay_factory):
        """Test phone number validation"""
        # Valid phone numbers
        stay = stay_factory(phone_number="+393334445566")
        stay.full_clean()
        assert stay.phone_number == "+393334445566"

        stay = stay_factory(phone_number="0233445566")
        stay.full_clean()
        assert stay.phone_number == "0233445566"

        # Invalid phone number should raise ValidationError
        with pytest.raises(ValidationError):
            stay = stay_factory(phone_number="invalid")
            stay.full_clean()
            stay.full_clean()

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

        stay = stay_factory(address="Nowhere")

        # Verify the coordinates were not set
        assert stay.latitude is None
        assert stay.longitude is None
