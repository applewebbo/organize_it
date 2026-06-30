import factory

from suggestions.models import AICredentials, SuggestionPreferences
from tests.accounts.factories import UserFactory


class AICredentialsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AICredentials

    user = factory.SubFactory(UserFactory)
    provider = AICredentials.Provider.GEMINI
    api_key_encrypted = "test-api-key"


class SuggestionPreferencesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SuggestionPreferences

    user = factory.SubFactory(UserFactory)
