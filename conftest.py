from pytest_factoryboy import register

from tests.accounts.factories import UserFactory
from tests.trips.factories import TripFactory

register(TripFactory)
register(UserFactory)
