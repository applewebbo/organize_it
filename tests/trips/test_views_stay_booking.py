import pytest
from django.test import override_settings

from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import StayBooking, TripCollaboration

pytestmark = pytest.mark.django_db


@override_settings(STAY22_AID="aid123")
class TestStayBookingViews(TestCase):
    def _setup(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        return user, trip

    def _make_multi_stage(self, trip):
        """Give the first day a distinct destination to create two stages."""
        day = trip.days.order_by("number").first()
        day.destination = "Testville"
        day.save()

    # --- modal / chooser ---------------------------------------------------

    def test_modal_single_stage_renders_and_creates_booking(self):
        user, trip = self._setup()
        with self.login(user):
            response = self.get("trips:stay-booking-modal", trip_pk=trip.pk)
        self.response_200(response)
        booking = StayBooking.objects.get(
            trip=trip, destination=trip.destination, created_by=user
        )
        assert booking.includes_author is True

    def test_modal_404_when_no_aid(self):
        user, trip = self._setup()
        with override_settings(STAY22_AID=""), self.login(user):
            response = self.get("trips:stay-booking-modal", trip_pk=trip.pk)
        self.response_404(response)

    def test_modal_multi_stage_shows_chooser(self):
        user, trip = self._setup()
        self._make_multi_stage(trip)
        with self.login(user):
            response = self.get("trips:stay-booking-modal", trip_pk=trip.pk)
        self.response_200(response)
        self.assertResponseContains("Testville", response, html=False)
        assert not StayBooking.objects.filter(trip=trip).exists()

    def test_modal_multi_stage_with_destination_renders_content(self):
        user, trip = self._setup()
        self._make_multi_stage(trip)
        with self.login(user):
            response = self.get(
                "trips:stay-booking-modal",
                trip_pk=trip.pk,
                data={"destination": "Testville"},
            )
        self.response_200(response)
        assert StayBooking.objects.filter(
            trip=trip, destination="Testville", created_by=user
        ).exists()

    # --- save --------------------------------------------------------------

    def test_save_sets_participants(self):
        user, trip = self._setup()
        collab = TripCollaboration.objects.create(
            trip=trip,
            participant_name="Anna",
            color="red",
            added_by=user,
            can_edit=False,
        )
        with self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={
                    "destination": trip.destination,
                    "includes_author": "on",
                    "participants": [collab.pk],
                },
            )
        self.response_200(response)
        booking = StayBooking.objects.get(trip=trip, created_by=user)
        assert booking.includes_author is True
        assert list(booking.participants.all()) == [collab]
        assert booking.adults == 2

    def test_save_unchecks_author(self):
        user, trip = self._setup()
        StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        with self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )
        self.response_200(response)
        booking = StayBooking.objects.get(trip=trip, created_by=user)
        assert booking.includes_author is False
        assert booking.participants.count() == 0

    def test_save_ignores_foreign_collaboration(self):
        user, trip = self._setup()
        other_trip = TripFactory()
        foreign = TripCollaboration.objects.create(
            trip=other_trip,
            participant_name="Ext",
            color="red",
            added_by=other_trip.author,
            can_edit=False,
        )
        with self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={"destination": trip.destination, "participants": [foreign.pk]},
            )
        self.response_200(response)
        booking = StayBooking.objects.get(trip=trip, created_by=user)
        assert booking.participants.count() == 0

    def test_save_sets_provider(self):
        user, trip = self._setup()
        with self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={"destination": trip.destination, "provider": "booking"},
            )
        self.response_200(response)
        booking = StayBooking.objects.get(trip=trip, created_by=user)
        assert booking.provider == "booking"

    def test_save_ignores_invalid_provider(self):
        user, trip = self._setup()
        StayBooking.objects.create(
            trip=trip,
            destination=trip.destination,
            created_by=user,
            provider="expedia",
        )
        with self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={"destination": trip.destination, "provider": "bogus"},
            )
        self.response_200(response)
        booking = StayBooking.objects.get(trip=trip, created_by=user)
        assert booking.provider == "expedia"

    def test_save_invalid_destination_404(self):
        user, trip = self._setup()
        with self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={"destination": "Nowhere"},
            )
        self.response_404(response)

    def test_save_404_when_no_aid(self):
        user, trip = self._setup()
        with override_settings(STAY22_AID=""), self.login(user):
            response = self.post(
                "trips:stay-booking-save",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )
        self.response_404(response)

    # --- redirect ----------------------------------------------------------

    def test_redirect_builds_stay22_url(self):
        user, trip = self._setup()
        StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        with self.login(user):
            response = self.get(
                "trips:stay-booking-redirect",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )
        assert response.status_code == 302
        location = response["Location"]
        assert location.startswith("https://www.stay22.com/allez/roam")
        assert "aid=aid123" in location

    def test_redirect_forces_provider_for_booking(self):
        user, trip = self._setup()
        StayBooking.objects.create(
            trip=trip,
            destination=trip.destination,
            created_by=user,
            provider="booking",
        )
        with self.login(user):
            response = self.get(
                "trips:stay-booking-redirect",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )
        assert response.status_code == 302
        location = response["Location"]
        assert location.startswith("https://www.stay22.com/allez/roam")
        assert "provider=booking" in location

    def test_redirect_defaults_to_trip_destination(self):
        user, trip = self._setup()
        StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        with self.login(user):
            response = self.get("trips:stay-booking-redirect", trip_pk=trip.pk)
        assert response.status_code == 302

    def test_redirect_404_without_booking(self):
        user, trip = self._setup()
        with self.login(user):
            response = self.get(
                "trips:stay-booking-redirect",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )
        self.response_404(response)

    def test_redirect_404_when_no_aid(self):
        user, trip = self._setup()
        StayBooking.objects.create(
            trip=trip, destination=trip.destination, created_by=user
        )
        with override_settings(STAY22_AID=""), self.login(user):
            response = self.get(
                "trips:stay-booking-redirect",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )
        self.response_404(response)

    def test_no_access_returns_404(self):
        user, trip = self._setup()
        other = self.make_user("other")
        with self.login(other):
            response = self.get("trips:stay-booking-modal", trip_pk=trip.pk)
        self.response_404(response)
