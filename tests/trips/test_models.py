# test_models.py
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.django_db


class TestTripModel:
    def test_trip_model_factory(self, user_factory, trip_factory):
        """Test trip model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")

        assert trip.__str__() == "Test Trip"
        assert trip.author == user

    @pytest.mark.parametrize(
        "start_date, end_date, status",
        [
            (date.today() + timedelta(days=10), date.today() + timedelta(days=12), 1),
            (date.today() + timedelta(days=4), date.today() + timedelta(days=6), 2),
            (date.today() - timedelta(days=1), date.today() + timedelta(days=1), 3),
            (date.today() - timedelta(days=10), date.today() - timedelta(days=8), 4),
        ],
    )
    def test_trip_status(
        self, user_factory, trip_factory, start_date, end_date, status
    ):
        user = user_factory()

        trip = trip_factory(
            author=user, title="Test Trip", start_date=start_date, end_date=end_date
        )

        print(start_date, end_date, status)

        assert trip.status == status
