# factories.py
import factory

from tests.accounts.factories import UserFactory
from trips.models import Trip


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trip

    author = factory.SubFactory(UserFactory)
    start_date = factory.Faker("date_between", start_date="today", end_date="+3d")
    end_date = factory.Faker("date_between", start_date="+4d", end_date="+7d")


class PlaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Place"

    address = factory.Faker("street_address")
    trip = factory.SubFactory(TripFactory)
