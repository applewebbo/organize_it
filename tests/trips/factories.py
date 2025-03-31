import random

import factory

from tests.accounts.factories import UserFactory

ITALIAN_CITIES = [
    "Roma",
    "Milano",
    "Firenze",
    "Venezia",
    "Napoli",
    "Bologna",
    "Torino",
    "Verona",
    "Genova",
    "Palermo",
]

CITY_ADDRESSES = {
    "Roma": [
        "Via del Corso 12",
        "Via Veneto 45",
        "Piazza Navona 3",
        "Via dei Fori Imperiali 24",
        "Via Condotti 8",
        "Via del Babuino 155",
        "Piazza di Spagna 20",
        "Via Sistina 77",
    ],
    "Milano": [
        "Via Montenapoleone 15",
        "Corso Buenos Aires 28",
        "Via Dante 4",
        "Corso Vittorio Emanuele II 16",
        "Via Torino 45",
        "Corso Sempione 32",
        "Via Brera 28",
        "Corso Garibaldi 71",
    ],
    "Firenze": [
        "Via dei Calzaiuoli 10",
        "Piazza della Signoria 5",
        "Via Tornabuoni 12",
        "Ponte Vecchio 24",
        "Via della Vigna Nuova 8",
        "Via Ghibellina 123",
        "Borgo San Jacopo 27",
        "Via Maggio 51",
    ],
    "Venezia": [
        "Riva degli Schiavoni 4196",
        "Campo Santa Margherita 2963",
        "Fondamenta Zattere 1413",
        "Campo San Polo 2198",
        "Calle Larga XXII Marzo 2398",
        "Strada Nova 3901",
        "Campo Santo Stefano 2957",
    ],
    "Napoli": [
        "Via Toledo 256",
        "Via Chiaia 89",
        "Via dei Tribunali 34",
        "Via San Gregorio Armeno 1",
        "Via Caracciolo 11",
        "Spaccanapoli 121",
        "Via Santa Lucia 166",
    ],
    "Bologna": [
        "Via dell'Indipendenza 67",
        "Via Rizzoli 32",
        "Via Zamboni 13",
        "Piazza Maggiore 6",
        "Via del Pratello 98",
        "Via Ugo Bassi 25",
        "Via D'Azeglio 15",
    ],
    "Torino": [
        "Via Roma 305",
        "Via Po 18",
        "Via Garibaldi 91",
        "Corso Vittorio Emanuele II 74",
        "Via Pietro Micca 12",
        "Corso Francia 145",
        "Via Lagrange 29",
    ],
    "Verona": [
        "Via Mazzini 27",
        "Corso Porta Borsari 17",
        "Via Cappello 23",
        "Piazza delle Erbe 28",
        "Corso Santa Anastasia 12",
        "Via Roma 33",
        "Via della Costa 11",
    ],
}

RESTAURANT_NAMES = [
    "Trattoria da Mario",
    "Osteria del Borgo",
    "Ristorante La Pergola",
    "Antica Osteria",
    "Da Luigi",
    "Il Gambero Rosso",
    "La Vecchia Roma",
    "Taverna dei Sapori",
    "La Cucina di Nonna",
    "Al Muretto",
    "Quattro Stagioni",
    "La Tavernetta",
    "Il Piccolo Mondo",
    "Osteria dell'Orso",
    "La Bottega del Vino",
    "Locanda del Mare",
]


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Trip"

    author = factory.SubFactory(UserFactory)
    title = factory.Faker("city", locale="it_IT")
    description = factory.Faker("sentence", nb_words=10)
    destination = factory.LazyAttribute(lambda obj: obj.title)
    start_date = factory.Faker("date_between", start_date="today", end_date="+3d")
    end_date = factory.Faker("date_between", start_date="+4d", end_date="+10d")


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


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Event"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")
        trip = factory.SubFactory(TripFactory)

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    trip = factory.LazyAttribute(lambda obj: obj.trip)
    name = factory.Faker("company", locale="it_IT")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(
        lambda obj: random.choice(
            CITY_ADDRESSES.get(obj.day.trip.destination, ["Via Roma 1"])
        )
    )
    category = factory.Faker("random_element", elements=[1, 2, 3])
    url = factory.Faker("url")


class TransportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Transport"

    class Params:
        location = factory.LazyAttribute(lambda obj: random.choice(ITALIAN_CITIES))
        dest_location = factory.LazyAttribute(lambda obj: random.choice(ITALIAN_CITIES))

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.LazyAttribute(lambda obj: f"{obj.location} - {obj.dest_location}")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(lambda obj: obj.location)
    destination = factory.LazyAttribute(lambda obj: obj.dest_location)
    type = factory.Faker("random_element", elements=[1, 2, 3, 4, 5, 6, 7])
    category = 1
    url = factory.Faker("url")


class ExperienceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Experience"

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.Faker(
        "random_element",
        elements=[
            "Duomo",
            "Castello Sforzesco",
            "Palazzo Reale",
            "Teatro Romano",
            "Basilica di San Marco",
            "Palazzo Ducale",
            "Torre Civica",
            "Museo Archeologico",
            "Pinacoteca",
            "Villa Reale",
            "Arena Romana",
            "Galleria d'Arte Moderna",
            "Parco Archeologico",
        ],
    )
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(
        lambda obj: random.choice(
            CITY_ADDRESSES.get(obj.day.trip.destination, ["Via Roma 1"])
        )
    )
    type = factory.Faker("random_element", elements=[1, 2, 3, 4, 5, 6])
    category = 2


class MealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Meal"

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.LazyAttribute(lambda obj: random.choice(RESTAURANT_NAMES))
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(
        lambda obj: random.choice(
            CITY_ADDRESSES.get(obj.day.trip.destination, ["Via Roma 1"])
        )
    )
    type = factory.Faker("random_element", elements=[1, 2, 3, 4])
    category = 3


class StayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Stay"

    name = factory.Faker(
        "random_element",
        elements=[
            "Hotel Belvedere",
            "Grand Hotel Milano",
            "Resort Luna Mare",
            "Camping Pineta Verde",
            "Hotel Excelsior",
            "Villa Paradiso",
            "Agriturismo Il Casale",
            "B&B La Terrazza",
            "Hotel Regina",
            "Ostello del Sole",
            "Resort Costa Azzurra",
            "Hotel Centrale",
        ],
    )
    check_in = factory.Faker("time")
    check_out = factory.Faker("time")
    cancellation_date = factory.Faker("future_date")
    phone_number = factory.Faker("phone_number", locale="it_IT")
    url = factory.Faker("url")
    address = factory.LazyAttribute(lambda obj: random.choice(ITALIAN_CITIES))
