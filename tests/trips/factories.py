# factories.py
import factory

from tests.accounts.factories import UserFactory
from trips.models import Trip


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trip

    author = factory.SubFactory(UserFactory)
