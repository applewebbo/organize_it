import factory

from suggestions.models import (
    AICredentials,
    DayPlanStop,
    SharedKeyNoticeDismissal,
    SuggestionPreferences,
)
from tests.accounts.factories import UserFactory
from tests.trips.factories import TripFactory


class AICredentialsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AICredentials

    user = factory.SubFactory(UserFactory)
    provider = AICredentials.Provider.GEMINI
    api_key_encrypted = "test-api-key"


class SharedKeyNoticeDismissalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SharedKeyNoticeDismissal

    user = factory.SubFactory(UserFactory)
    trip = factory.SubFactory(TripFactory)


class SuggestionPreferencesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SuggestionPreferences

    user = factory.SubFactory(UserFactory)


class DayPlanStopFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DayPlanStop

    day = factory.LazyAttribute(lambda o: TripFactory().days.first())
    strategy = "add"
    kind = "experience"
    name = factory.Faker("company")
