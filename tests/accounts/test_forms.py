import pytest

from accounts.forms import ProfileUpdateForm
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db


class TestProfileUpdateForm:
    def test_fav_trip_queryset_excludes_archived_trips(self, user_factory):
        """Test that fav_trip field only includes non-archived trips"""
        user = user_factory()
        active_trip = TripFactory(author=user, status=1)  # NOT_STARTED
        archived_trip = TripFactory(author=user, status=5)  # ARCHIVED

        form = ProfileUpdateForm(instance=user.profile)

        # Check that queryset includes active trip but not archived
        fav_trip_queryset = form.fields["fav_trip"].queryset
        assert active_trip in fav_trip_queryset
        assert archived_trip not in fav_trip_queryset

    def test_fav_trip_queryset_filters_by_user(self, user_factory):
        """Test that fav_trip field only includes trips from the user"""
        user1 = user_factory()
        user2 = user_factory()
        user1_trip = TripFactory(author=user1, status=1)
        user2_trip = TripFactory(author=user2, status=1)

        form = ProfileUpdateForm(instance=user1.profile)

        fav_trip_queryset = form.fields["fav_trip"].queryset
        assert user1_trip in fav_trip_queryset
        assert user2_trip not in fav_trip_queryset
