from pytest_factoryboy import register

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ExperienceFactory,
    LinkFactory,
    MealFactory,
    NoteFactory,
    PlaceFactory,
    StayFactory,
    TransportFactory,
    TripFactory,
)

register(TripFactory)
register(UserFactory)
register(PlaceFactory)
register(LinkFactory)
register(NoteFactory)
register(MealFactory)
register(StayFactory)
register(TransportFactory)
register(ExperienceFactory)
