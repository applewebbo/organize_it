# test_models.py
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.conf import settings

from trips.models import (
    Event,
    Experience,
    Meal,
    Stay,
    Trip,
)

pytestmark = pytest.mark.django_db


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

    @patch("geocoder.mapbox")
    def test_destination_geocoding_constrained_to_place(
        self, mock_geocoder, user_factory, trip_factory
    ):
        """The destination is geocoded at place level so an ambiguous name
        (e.g. "Roma") cannot match a country instead of the city."""
        mock_geocoder.return_value.latlng = [41.9028, 12.4964]
        trip_factory(
            author=user_factory(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            destination="Roma",
        )
        assert mock_geocoder.call_args.kwargs["types"] == "place"


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

    def test_single_day_trip_triggers_one_home_transfer_task(
        self, user_factory, trip_factory
    ):
        """Single-day trip: only one calculate_day_transfer task is queued on creation."""
        from unittest.mock import patch

        with patch("django_q.tasks.async_task") as mock_async:
            trip = trip_factory(
                author=user_factory(),
                start_date=date.today(),
                end_date=date.today(),
            )
        assert trip.days.count() == 1
        called_pks = [call.args[1] for call in mock_async.call_args_list]
        day_pk = trip.days.first().pk
        assert called_pks.count(day_pk) >= 1
        assert len(set(called_pks)) == 1

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

    @patch("geocoder.mapbox")
    def test_new_days_get_trip_destination(
        self, mock_geocoder, user_factory, trip_factory
    ):
        """New days created via signal receive trip.destination with geocoded coords."""
        mock_geocoder.return_value.latlng = [45.4654, 9.1866]
        trip = trip_factory(
            author=user_factory(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            destination="Milano",
        )
        for day in trip.days.all():
            assert day.destination == "Milano"

    @patch("geocoder.mapbox")
    def test_trip_destination_change_updates_non_customized_days(
        self, mock_geocoder, user_factory, trip_factory
    ):
        """When trip.destination changes, days still matching old destination are updated; customized days are not."""
        mock_geocoder.return_value.latlng = [45.4654, 9.1866]
        trip = trip_factory(
            author=user_factory(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            destination="Milano",
        )
        # Customize day 1 destination
        day1 = trip.days.get(number=1)
        day1.destination = "Bergamo"
        day1.save(update_fields=["destination"])

        mock_geocoder.return_value.latlng = [41.8967, 12.4822]
        trip.destination = "Roma"
        trip.save()

        day1.refresh_from_db()
        day2 = trip.days.get(number=2)
        day3 = trip.days.get(number=3)

        # Customized day unchanged
        assert day1.destination == "Bergamo"
        # Non-customized days updated
        assert day2.destination == "Roma"
        assert day3.destination == "Roma"

    @patch("geocoder.mapbox")
    def test_capture_old_destination_handles_deleted_trip(
        self, mock_geocoder, user_factory
    ):
        """pre_save signal sets _old_destination=None when trip pk exists but record is gone."""
        from trips.models import capture_trip_old_destination

        mock_geocoder.return_value.latlng = None
        trip = Trip(
            pk=999999,
            author=user_factory(),
            title="Ghost Trip",
            destination="Firenze",
        )
        # pk is set but no DB record → DoesNotExist → _old_destination = None
        capture_trip_old_destination(sender=Trip, instance=trip)
        assert trip._old_destination is None

    def test_group_days_by_destination_empty(self):
        """group_days_by_destination returns None for empty list."""
        from trips.utils import group_days_by_destination

        assert group_days_by_destination([]) is None

    def test_group_days_by_destination_single_destination(
        self, user_factory, trip_factory
    ):
        """group_days_by_destination returns None when all days share one destination."""
        from trips.utils import group_days_by_destination

        trip = trip_factory(author=user_factory(), destination="")
        for day in trip.days.all():
            day.destination = "Roma"
            day.save(update_fields=["destination"])
        assert group_days_by_destination(trip.days.all()) is None

    def test_group_days_by_destination_multi(self, user_factory, trip_factory):
        """group_days_by_destination groups consecutive days with different destinations."""
        from datetime import date, timedelta

        from trips.utils import group_days_by_destination

        trip = trip_factory(
            author=user_factory(),
            destination="",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )
        days = list(trip.days.order_by("number"))
        days[0].destination = "Roma"
        days[1].destination = "Roma"
        days[2].destination = "Napoli"
        days[3].destination = "Roma"
        for day in days:
            day.save(update_fields=["destination"])

        groups = group_days_by_destination(trip.days.order_by("number"))
        assert groups is not None
        assert len(groups) == 3
        assert groups[0]["destination"] == "Roma"
        assert groups[0]["days"] == [days[0], days[1]]
        assert groups[0]["next_destination"] == "Napoli"
        assert groups[1]["destination"] == "Napoli"
        assert groups[1]["days"] == [days[2]]
        assert groups[1]["next_destination"] == "Roma"
        assert groups[2]["destination"] == "Roma"
        assert groups[2]["days"] == [days[3]]
        assert groups[2]["next_destination"] is None


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

        assert event.__str__() == event.name
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
            address="Milan, Italy",
        )

        # Reset mock before saving again
        mock_geocoder.reset_mock()

        # Save again without changing the address
        event.name = "Updated Event Name"
        event.save()

        # Verify geocoder was not called again
        mock_geocoder.assert_not_called()

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
        mock_geocoder.assert_called_with(
            "Colosseum, Roma", access_token=settings.MAPBOX_ACCESS_TOKEN
        )
        assert event.latitude == 41.890251
        assert event.longitude == 12.492373

    @patch("geocoder.mapbox")
    def test_event_geocoding_failure(self, mock_geocoder, event_factory):
        """Test geocoding failure leaves coordinates unchanged"""
        mock_geocoder.return_value.latlng = None
        event = event_factory(address="Nowhere", latitude=None, longitude=None)
        assert event.latitude is None
        assert event.longitude is None


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

    @patch("geocoder.mapbox")
    def test_stay_geocoding_without_city(self, mock_geocoder):
        """Test geocoding uses only address when city is empty"""
        mock_geocoder.return_value.latlng = [45.4642, 9.1900]

        stay = Stay.objects.create(
            name="Hotel Test",
            address="Via Roma 123",
            city="",  # Empty city
            latitude=None,
            longitude=None,
        )

        mock_geocoder.assert_called_once_with(
            "Via Roma 123", access_token=settings.MAPBOX_ACCESS_TOKEN
        )
        assert stay.latitude == 45.4642
        assert stay.longitude == 9.1900


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
                "company": "Trenitalia",
                "company_website": "https://trenitalia.com",
            },
        )

        assert transfer.train_number == "FR9612"
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

    def test_main_transfer_car_with_valid_addresses(self, trip_factory):
        """Test that car transfers pass validation with both addresses"""
        from trips.models import MainTransfer

        trip = trip_factory()

        transfer = MainTransfer(
            trip=trip,
            type=MainTransfer.Type.CAR,
            direction=MainTransfer.Direction.ARRIVAL,
            origin_name="Origin Location",
            destination_name="Destination Location",
            origin_address="Piazza Duomo, Milano",
            destination_address="Via Roma 123, Milano",
            start_time="10:00",
            end_time="12:00",
        )

        # Should not raise ValidationError
        transfer.full_clean()
        assert transfer.type == MainTransfer.Type.CAR

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


class TestEventGoogleMapsDirections:
    """Tests for Event.google_maps_directions_url property"""

    def test_returns_url_with_address(self, trip_factory, experience_factory):
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(
            trip=trip, day=day, address="Via Roma 1", city="Milano"
        )
        assert event.google_maps_directions_url is not None
        assert "google.com/maps" in event.google_maps_directions_url
        assert "destination" in event.google_maps_directions_url

    def test_returns_url_with_coordinates_only(self, trip_factory, experience_factory):
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(trip=trip, day=day)
        Event.objects.filter(pk=event.pk).update(
            address="", city="", latitude=45.0, longitude=9.0
        )
        event.refresh_from_db()
        assert event.google_maps_directions_url is not None
        assert "45.0,9.0" in event.google_maps_directions_url

    @patch("geocoder.mapbox")
    def test_returns_none_without_address_or_coords(
        self, mock_geocoder, trip_factory, experience_factory
    ):
        mock_geocoder.return_value.latlng = None
        trip = trip_factory()
        day = trip.days.first()
        event = experience_factory(trip=trip, day=day)
        Event.objects.filter(pk=event.pk).update(
            address="", city="", latitude=None, longitude=None
        )
        event.refresh_from_db()
        assert event.google_maps_directions_url is None


class TestMainTransferConnection:
    """Tests for MainTransferConnection model"""

    def test_arrival_connection_to_event_creation(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test creating an arrival connection to an event"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        event = experience_factory(trip=trip, day=first_day)

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        assert connection.main_transfer == main_transfer
        assert connection.event == event
        assert connection.stay is None
        assert connection.transport_mode == "driving"
        assert connection.destination_type == "event"
        assert connection.destination == event

    def test_arrival_connection_to_stay_creation(
        self, trip_factory, main_transfer_factory, stay_factory
    ):
        """Test creating an arrival connection to a stay"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        stay = stay_factory()
        first_day.stay = stay
        first_day.save()

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, stay=stay, transport_mode="transit"
        )

        assert connection.main_transfer == main_transfer
        assert connection.stay == stay
        assert connection.event is None
        assert connection.transport_mode == "transit"
        assert connection.destination_type == "stay"
        assert connection.destination == stay

    def test_departure_connection_to_event_creation(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test creating a departure connection from an event"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.DEPARTURE
        )
        last_day = trip.days.last()
        event = experience_factory(trip=trip, day=last_day)

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        assert connection.main_transfer == main_transfer
        assert connection.event == event
        assert connection.stay is None

    def test_connection_onetoone_constraint(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test that OneToOne constraint prevents duplicate connections"""
        from django.db import IntegrityError

        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        event1 = experience_factory(trip=trip, day=first_day)
        event2 = experience_factory(trip=trip, day=first_day)

        # Create first connection
        MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event1, transport_mode="driving"
        )

        # Try to create another connection for the same main_transfer (should fail)
        with pytest.raises(IntegrityError):
            MainTransferConnection.objects.create(
                main_transfer=main_transfer, event=event2, transport_mode="walking"
            )

    def test_connection_validation_no_destination(
        self, trip_factory, main_transfer_factory
    ):
        """Test that connection requires either event or stay"""
        from django.core.exceptions import ValidationError

        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )

        connection = MainTransferConnection(
            main_transfer=main_transfer, transport_mode="driving"
        )

        with pytest.raises(ValidationError) as exc_info:
            connection.full_clean()

        assert "Either event or stay must be set" in str(exc_info.value)

    def test_connection_validation_both_destinations(
        self, trip_factory, main_transfer_factory, experience_factory, stay_factory
    ):
        """Test that connection cannot have both event and stay"""
        from django.core.exceptions import ValidationError

        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        event = experience_factory(trip=trip, day=first_day)
        stay = stay_factory()

        connection = MainTransferConnection(
            main_transfer=main_transfer,
            event=event,
            stay=stay,
            transport_mode="driving",
        )

        with pytest.raises(ValidationError) as exc_info:
            connection.full_clean()

        assert "Cannot set both event and stay" in str(exc_info.value)

    def test_arrival_connection_properties(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test properties for arrival connection"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.ARRIVAL,
            destination_name="JFK Airport",
            destination_latitude=40.6413,
            destination_longitude=-73.7781,
        )
        first_day = trip.days.first()
        event = experience_factory(
            trip=trip, day=first_day, latitude=40.7580, longitude=-73.9855
        )

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        # For ARRIVAL: from main_transfer destination to event
        assert connection.from_location == "JFK Airport"
        assert connection.to_location == event.name
        assert connection.from_coordinates == (40.6413, -73.7781)
        assert connection.to_coordinates == (40.7580, -73.9855)

    def test_arrival_connection_properties_with_stay(
        self, trip_factory, main_transfer_factory, stay_factory
    ):
        """Test properties for arrival connection to stay"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.ARRIVAL,
            destination_name="JFK Airport",
            destination_latitude=40.6413,
            destination_longitude=-73.7781,
        )
        first_day = trip.days.first()
        stay = stay_factory(latitude=40.7580, longitude=-73.9855)
        first_day.stay = stay
        first_day.save()

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, stay=stay, transport_mode="driving"
        )

        # For ARRIVAL: from main_transfer destination to stay
        assert connection.from_location == "JFK Airport"
        assert connection.to_location == stay.name
        assert connection.from_coordinates == (40.6413, -73.7781)
        assert connection.to_coordinates == (40.7580, -73.9855)

    def test_departure_connection_properties(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test properties for departure connection"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="JFK Airport",
            origin_latitude=40.6413,
            origin_longitude=-73.7781,
        )
        last_day = trip.days.last()
        event = experience_factory(
            trip=trip, day=last_day, latitude=40.7580, longitude=-73.9855
        )

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        # For DEPARTURE: from event to main_transfer origin
        assert connection.from_location == event.name
        assert connection.to_location == "JFK Airport"
        assert connection.from_coordinates == (40.7580, -73.9855)
        assert connection.to_coordinates == (40.6413, -73.7781)

    def test_departure_connection_properties_with_stay(
        self, trip_factory, main_transfer_factory, stay_factory
    ):
        """Test properties for departure connection from stay"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="JFK Airport",
            origin_latitude=40.6413,
            origin_longitude=-73.7781,
        )
        last_day = trip.days.last()
        stay = stay_factory(latitude=40.7580, longitude=-73.9855)
        last_day.stay = stay
        last_day.save()

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, stay=stay, transport_mode="driving"
        )

        # For DEPARTURE: from stay to main_transfer origin
        assert connection.from_location == stay.name
        assert connection.to_location == "JFK Airport"
        assert connection.from_coordinates == (40.7580, -73.9855)
        assert connection.to_coordinates == (40.6413, -73.7781)

    def test_connection_google_maps_url(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test google_maps_url generation"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.ARRIVAL,
            destination_latitude=40.6413,
            destination_longitude=-73.7781,
        )
        first_day = trip.days.first()
        event = experience_factory(
            trip=trip, day=first_day, latitude=40.7580, longitude=-73.9855
        )

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        assert connection.google_maps_url is not None
        assert "google.com/maps" in connection.google_maps_url
        assert "40.6413,-73.7781" in connection.google_maps_url
        assert "40.758,-73.9855" in connection.google_maps_url
        assert "travelmode=driving" in connection.google_maps_url

    def test_connection_google_maps_url_without_coordinates(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test google_maps_url returns None when coordinates missing"""
        from trips.models import Event, MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip,
            direction=MainTransfer.Direction.ARRIVAL,
            destination_latitude=None,
            destination_longitude=None,
        )
        first_day = trip.days.first()
        event = experience_factory(trip=trip, day=first_day)
        # Remove coordinates using update to bypass geocoding signal
        Event.objects.filter(pk=event.pk).update(latitude=None, longitude=None)
        event.refresh_from_db()

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        assert connection.google_maps_url is None

    def test_connection_str_method(
        self, trip_factory, main_transfer_factory, experience_factory
    ):
        """Test __str__ method"""
        from trips.models import MainTransfer, MainTransferConnection

        trip = trip_factory()
        main_transfer = main_transfer_factory(
            trip=trip, direction=MainTransfer.Direction.ARRIVAL
        )
        first_day = trip.days.first()
        event = experience_factory(trip=trip, day=first_day)

        connection = MainTransferConnection.objects.create(
            main_transfer=main_transfer, event=event, transport_mode="driving"
        )

        str_repr = str(connection)
        assert "Arrival Connection" in str_repr
        assert event.name in str_repr


class TestTripCollaboration:
    def test_str(self, user_factory, trip_factory):
        from trips.models import TripCollaboration

        user = user_factory()
        trip = trip_factory()
        collab = TripCollaboration.objects.create(
            trip=trip, user=user, color="blue", added_by=trip.author
        )
        assert str(user) in str(collab)
        assert trip.title in str(collab)
        assert "blue" in str(collab)

    def test_next_free_color_returns_first_unused(self, user_factory, trip_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        user1 = user_factory()
        user2 = user_factory()
        TripCollaboration.objects.create(
            trip=trip, user=user1, color="blue", added_by=trip.author
        )
        color = TripCollaboration.next_free_color(trip)
        assert color == "green"

        TripCollaboration.objects.create(
            trip=trip, user=user2, color="green", added_by=trip.author
        )
        color = TripCollaboration.next_free_color(trip)
        assert color == "purple"

    def test_next_free_color_wraps_when_all_used(self, trip_factory, user_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        for color in TripCollaboration.PALETTE_VALUES:
            user = user_factory()
            TripCollaboration.objects.create(
                trip=trip, user=user, color=color, added_by=trip.author
            )
        color = TripCollaboration.next_free_color(trip)
        assert color == TripCollaboration.PALETTE_VALUES[0]

    def test_display_name_named_only(self, trip_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        collab = TripCollaboration.objects.create(
            trip=trip,
            user=None,
            participant_name="Marco",
            color="blue",
            added_by=trip.author,
            can_edit=False,
        )
        assert collab.display_name == "Marco"
        assert collab.is_named_only is True
        assert "Marco" in str(collab)

    def test_display_name_email_viewer(self, trip_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        collab = TripCollaboration.objects.create(
            trip=trip,
            user=None,
            participant_email="viewer@example.com",
            color="blue",
            added_by=trip.author,
            can_edit=False,
        )
        assert collab.display_name == "viewer@example.com"
        assert collab.is_named_only is False

    def test_defaults_adult_no_age(self, trip_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        collab = TripCollaboration.objects.create(
            trip=trip,
            user=None,
            participant_name="Marco",
            color="blue",
            added_by=trip.author,
        )
        assert collab.is_child is False
        assert collab.age is None

    def test_child_with_age(self, trip_factory):
        from trips.models import TripCollaboration

        trip = trip_factory()
        collab = TripCollaboration.objects.create(
            trip=trip,
            user=None,
            participant_name="Sofia",
            color="blue",
            added_by=trip.author,
            is_child=True,
            age=8,
        )
        assert collab.is_child is True
        assert collab.age == 8


class TestTripInvitation:
    def test_str(self, user_factory, trip_factory):
        from datetime import datetime, timezone

        from trips.models import TripInvitation

        trip = trip_factory()
        invitation = TripInvitation.objects.create(
            trip=trip,
            email="guest@example.com",
            invited_by=trip.author,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        assert "guest@example.com" in str(invitation)
        assert trip.title in str(invitation)

    def test_is_valid_true(self, user_factory, trip_factory):
        from datetime import datetime, timezone

        from trips.models import TripInvitation

        trip = trip_factory()
        invitation = TripInvitation.objects.create(
            trip=trip,
            email="guest@example.com",
            invited_by=trip.author,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        assert invitation.is_valid is True

    def test_is_valid_false_when_accepted(self, trip_factory):
        from datetime import datetime, timezone

        from django.utils import timezone as dj_tz

        from trips.models import TripInvitation

        trip = trip_factory()
        invitation = TripInvitation.objects.create(
            trip=trip,
            email="guest@example.com",
            invited_by=trip.author,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            is_accepted=True,
            accepted_at=dj_tz.now(),
        )
        assert invitation.is_valid is False

    def test_is_valid_false_when_expired(self, trip_factory):
        from datetime import datetime, timezone

        from trips.models import TripInvitation

        trip = trip_factory()
        invitation = TripInvitation.objects.create(
            trip=trip,
            email="guest@example.com",
            invited_by=trip.author,
            expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
        assert invitation.is_valid is False

    def test_get_absolute_url(self, trip_factory):
        from datetime import datetime, timezone
        from unittest.mock import patch

        from trips.models import TripInvitation

        trip = trip_factory()
        invitation = TripInvitation.objects.create(
            trip=trip,
            email="guest@example.com",
            invited_by=trip.author,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        with patch(
            "trips.models.reverse",
            return_value=f"/trips/invite/{invitation.token}/accept/",
        ):
            url = invitation.get_absolute_url()
        assert str(invitation.token) in url
