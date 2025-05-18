from pytest_factoryboy import register

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    LinkFactory,
    MealFactory,
    StayFactory,
    TransportFactory,
    TripFactory,
)

register(TripFactory)
register(UserFactory)
register(LinkFactory)
register(MealFactory)
register(StayFactory)
register(TransportFactory)
register(ExperienceFactory)
register(EventFactory)
