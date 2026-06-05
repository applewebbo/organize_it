from pytest_factoryboy import register

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ChecklistItemFactory,
    EventFactory,
    ExperienceFactory,
    LinkFactory,
    MainTransferFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)

register(TripFactory)
register(UserFactory)
register(LinkFactory)
register(MealFactory)
register(StayFactory)
register(ExperienceFactory)
register(EventFactory)
register(MainTransferFactory)
register(ChecklistItemFactory)
