# factories.py
import factory

from tests.accounts.factories import UserFactory
from trips.models import Trip


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trip

    author = factory.SubFactory(UserFactory)
    # start_date = factory.Faker("date_between", start_date='+8d', end_date='+10d')
    # end_date = factory.Faker("date_between", start_date='+11d', end_date='+14d')
