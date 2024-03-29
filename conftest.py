from pytest_factoryboy import register

from tests.accounts.factories import UserFactory
from tests.trips.factories import LinkFactory, NoteFactory, PlaceFactory, TripFactory

register(TripFactory)
register(UserFactory)
register(PlaceFactory)
register(LinkFactory)
register(NoteFactory)
