# factories.py
import factory

from tests.accounts.factories import UserFactory


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Trip"

    author = factory.SubFactory(UserFactory)
    title = factory.Faker("city", locale="it_IT")
    description = factory.Faker("sentence", nb_words=10)
    destination = factory.LazyAttribute(lambda obj: obj.title)
    start_date = factory.Faker("date_between", start_date="today", end_date="+3d")
    end_date = factory.Faker("date_between", start_date="+4d", end_date="+7d")


class PlaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Place"

    name = factory.Faker("street_name")
    address = factory.Faker("street_address")
    trip = factory.SubFactory(TripFactory)


class PlaceItFactory(factory.django.DjangoModelFactory):
    """Factory for populate the database with places located in Italy"""

    class Meta:
        model = "trips.Place"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")

    name = factory.LazyAttribute(lambda obj: obj.location[2])
    address = factory.LazyAttribute(lambda obj: obj.location[2])
    latitude = factory.LazyAttribute(lambda obj: obj.location[0])
    longitude = factory.LazyAttribute(lambda obj: obj.location[1])
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


class TransportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Transport"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")
        dest_location = factory.Faker("local_latlng", country_code="IT")

    trip = factory.SubFactory(TripFactory)
    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.Faker("company", locale="it_IT")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(lambda obj: obj.location[2])
    destination = factory.LazyAttribute(lambda obj: obj.dest_location[2])
    type = factory.Faker("random_element", elements=[1, 2, 3, 4, 5, 6, 7])
    category = 1


class ExperienceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Experience"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")

    trip = factory.SubFactory(TripFactory)
    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.Faker("company", locale="it_IT")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(lambda obj: obj.location[2])
    type = factory.Faker("random_element", elements=[1, 2, 3, 4, 5, 6])
    category = 2


class MealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Meal"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")

    trip = factory.SubFactory(TripFactory)
    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.Faker("company", locale="it_IT")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(lambda obj: obj.location[2])
    type = factory.Faker("random_element", elements=[1, 2, 3, 4])
    category = 3


class StayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Stay"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")

    name = factory.Faker("company", locale="it_IT")
    check_in = factory.Faker("time")
    check_out = factory.Faker("time")
    cancellation_date = factory.Faker("future_date")
    phone_number = factory.Faker("phone_number", locale="it_IT")
    url = factory.Faker("url")
    address = factory.LazyAttribute(lambda obj: obj.location[2])
