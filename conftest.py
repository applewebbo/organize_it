from pytest_factoryboy import register

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ChecklistItemFactory,
    EventFactory,
    ExpenseFactory,
    ExpenseParticipantFactory,
    ExpenseShareFactory,
    ExperienceFactory,
    FamilyUnitFactory,
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
register(FamilyUnitFactory)
register(ExpenseParticipantFactory)
register(ExpenseFactory)
register(ExpenseShareFactory)
