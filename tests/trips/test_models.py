# test_models.py
import pytest


@pytest.mark.django_db
class TestTripModel:
    def test_trip_model(self, user_factory, trip_factory):
        # Create a user
        user = user_factory()

        # Create a trip
        trip = trip_factory(author=user, title="Test Trip")

        # Test __str__ method
        assert trip.__str__() == "Test Trip"
