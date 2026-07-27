import pytest
from django.db.utils import IntegrityError

from trips.models import StayBooking, TripCollaboration

pytestmark = pytest.mark.django_db


@pytest.fixture
def booking_setup(user_factory, trip_factory):
    user = user_factory()
    trip = trip_factory(author=user)
    return trip, user


class TestStayBooking:
    def test_str(self, booking_setup):
        trip, user = booking_setup
        booking = StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        assert trip.destination in str(booking)
        assert trip.title in str(booking)

    def test_defaults(self, booking_setup):
        trip, user = booking_setup
        booking = StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        assert booking.includes_author is True
        assert booking.provider == StayBooking.Provider.SMART
        assert booking.hotel_name == ""
        assert booking.adults == 1
        assert booking.children == 0

    def test_adults_counts_author_and_adult_participants(self, booking_setup):
        trip, user = booking_setup
        booking = StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        adult = TripCollaboration.objects.create(
            trip=trip,
            participant_name="Anna",
            color="red",
            added_by=user,
            can_edit=False,
        )
        booking.participants.add(adult)
        assert booking.adults == 2
        assert booking.children == 0

    def test_children_counts_child_participants(self, booking_setup):
        trip, user = booking_setup
        booking = StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        child = TripCollaboration.objects.create(
            trip=trip,
            participant_name="Leo",
            is_child=True,
            age=6,
            color="blue",
            added_by=user,
            can_edit=False,
        )
        booking.participants.add(child)
        assert booking.adults == 1
        assert booking.children == 1

    def test_adults_excludes_author_when_not_included(self, booking_setup):
        trip, user = booking_setup
        booking = StayBooking.objects.create(
            trip=trip,
            destination=trip.destination,
            created_by=user,
            includes_author=False,
        )
        assert booking.adults == 0

    def test_unique_trip_destination_created_by(self, booking_setup):
        trip, user = booking_setup
        StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        with pytest.raises(IntegrityError):
            StayBooking.objects.create(
                trip=trip, destination=trip.destination, created_by=user
            )
