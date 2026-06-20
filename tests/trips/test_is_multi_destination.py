import pytest

from trips.models import Trip

pytestmark = pytest.mark.django_db


def test_is_multi_destination_without_pk():
    trip = Trip(title="New Trip")
    assert not trip.is_multi_destination
