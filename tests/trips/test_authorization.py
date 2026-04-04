"""Tests for collaboration authorization helpers."""

import pytest
from django.http import Http404

pytestmark = pytest.mark.django_db


class TestAccessibleTripsQs:
    def test_returns_owned_trips(self, user_factory, trip_factory):
        from trips.utils import accessible_trips_qs

        user = user_factory()
        trip = trip_factory(author=user)
        assert trip in accessible_trips_qs(user)

    def test_returns_collaborated_trips(self, user_factory, trip_factory):
        from trips.models import TripCollaboration
        from trips.utils import accessible_trips_qs

        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        assert trip in accessible_trips_qs(collab)

    def test_excludes_unrelated_trips(self, user_factory, trip_factory):
        from trips.utils import accessible_trips_qs

        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        assert trip not in accessible_trips_qs(stranger)

    def test_no_duplicates_when_collaborator(self, user_factory, trip_factory):
        from trips.models import TripCollaboration
        from trips.utils import accessible_trips_qs

        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        qs = accessible_trips_qs(collab)
        assert qs.filter(pk=trip.pk).count() == 1


class TestGetTripOr404:
    def test_owner_can_access(self, user_factory, trip_factory):
        from trips.utils import get_trip_or_404

        user = user_factory()
        trip = trip_factory(author=user)
        result = get_trip_or_404(trip.pk, user)
        assert result == trip

    def test_collaborator_can_access(self, user_factory, trip_factory):
        from trips.models import TripCollaboration
        from trips.utils import get_trip_or_404

        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="green", added_by=owner
        )
        result = get_trip_or_404(trip.pk, collab)
        assert result == trip

    def test_stranger_gets_404(self, user_factory, trip_factory):
        from trips.utils import get_trip_or_404

        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        with pytest.raises(Http404):
            get_trip_or_404(trip.pk, stranger)


class TestGetTripForOwnerOr404:
    def test_owner_can_access(self, user_factory, trip_factory):
        from trips.utils import get_trip_for_owner_or_404

        user = user_factory()
        trip = trip_factory(author=user)
        result = get_trip_for_owner_or_404(trip.pk, user)
        assert result == trip

    def test_collaborator_gets_404(self, user_factory, trip_factory):
        from trips.models import TripCollaboration
        from trips.utils import get_trip_for_owner_or_404

        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="purple", added_by=owner
        )
        with pytest.raises(Http404):
            get_trip_for_owner_or_404(trip.pk, collab)

    def test_stranger_gets_404(self, user_factory, trip_factory):
        from trips.utils import get_trip_for_owner_or_404

        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        with pytest.raises(Http404):
            get_trip_for_owner_or_404(trip.pk, stranger)
