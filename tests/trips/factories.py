# factories.py
import factory

from tests.accounts.factories import UserFactory


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Trip"

    author = factory.SubFactory(UserFactory)
    start_date = factory.Faker("date_between", start_date="today", end_date="+3d")
    end_date = factory.Faker("date_between", start_date="+4d", end_date="+7d")


class PlaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Place"

    address = factory.Faker("street_address")
    trip = factory.SubFactory(TripFactory)


class LinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Link"

    author = factory.SubFactory(UserFactory)
    url = factory.Faker("url")
    title = factory.Faker("sentence")


class NoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Note"

    content = factory.Faker("paragraph", nb_sentences=4)
    trip = factory.SubFactory(TripFactory)
