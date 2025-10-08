import random

import factory

from tests.accounts.factories import UserFactory

PLACES = {
    "Roma": {
        "hotels": [
            {"name": "Hotel Splendide Royal", "address": "Via di Porta Pinciana 14"},
            {"name": "The St. Regis Rome", "address": "Via Vittorio E. Orlando 3"},
            {"name": "Hotel Eden", "address": "Via Ludovisi 49"},
            {"name": "Hotel Palazzo Manfredi", "address": "Via Labicana 125"},
            {"name": "Villa Spalletti Trivelli", "address": "Via Piacenza 4"},
            {
                "name": "Anantara Palazzo Naiadi Hotel",
                "address": "Piazza della Repubblica 48",
            },
        ],
        "restaurants": [
            {"name": "La Pergola", "address": "Via Alberto Cadlolo 101"},
            {"name": "Il Pagliaccio", "address": "Via dei Banchi Vecchi 129a"},
            {
                "name": "Roscioli Salumeria con Cucina",
                "address": "Via dei Giubbonari 21",
            },
            {"name": "Armando al Pantheon", "address": "Salita de' Crescenzi 31"},
            {"name": "Da Cesare al Casaletto", "address": "Via del Casaletto 45"},
            {"name": "Trattoria Monti", "address": "Via di S. Vito 13"},
        ],
        "attractions": [
            {"name": "Colosseo", "address": "Piazza del Colosseo 1"},
            {"name": "Foro Romano", "address": "Largo della Salara Vecchia 5/6"},
            {"name": "Pantheon", "address": "Piazza della Rotonda"},
            {"name": "Fontana di Trevi", "address": "Piazza di Trevi"},
            {"name": "Musei Vaticani", "address": "Viale Vaticano"},
            {"name": "Piazza Navona", "address": "Piazza Navona"},
        ],
    },
    "Milano": {
        "hotels": [
            {
                "name": "Bulgari Hotel Milano",
                "address": "Via Privata Fratelli Gabba 7b",
            },
            {"name": "Armani Hotel Milano", "address": "Via Alessandro Manzoni 31"},
            {"name": "Park Hyatt Milano", "address": "Via Tommaso Grossi 1"},
            {"name": "Grand Hotel et de Milan", "address": "Via Manzoni 29"},
            {
                "name": "Palazzo Parigi Hotel & Grand Spa",
                "address": "Corso di Porta Nuova 1",
            },
            {"name": "Four Seasons Hotel Milano", "address": "Via Gesù 6/8"},
        ],
        "restaurants": [
            {"name": "Enrico Bartolini al MUDEC", "address": "Via Tortona 56"},
            {"name": "Seta by Antonio Guida", "address": "Via Andegari 9"},
            {"name": "Cracco", "address": "Galleria Vittorio Emanuele II"},
            {
                "name": "Il Luogo di Aimo e Nadia",
                "address": "Via Privata Raimondo Montecuccoli 6",
            },
            {"name": "Trippa Milano", "address": "Via Giorgio Vasari 1"},
            {"name": "Ratanà", "address": "Via Gaetano de Castillia 28"},
        ],
        "attractions": [
            {"name": "Duomo di Milano", "address": "Piazza del Duomo"},
            {"name": "Galleria Vittorio Emanuele II", "address": "Piazza del Duomo"},
            {"name": "Teatro alla Scala", "address": "Via Filodrammatici 2"},
            {"name": "Castello Sforzesco", "address": "Piazza Castello"},
            {"name": "Pinacoteca di Brera", "address": "Via Brera 28"},
            {
                "name": "Santa Maria delle Grazie",
                "address": "Piazza di Santa Maria delle Grazie",
            },
        ],
    },
    "Firenze": {
        "hotels": [
            {"name": "Four Seasons Hotel Firenze", "address": "Borgo Pinti 99"},
            {"name": "The St. Regis Florence", "address": "Piazza Ognissanti 1"},
            {"name": "Hotel Lungarno", "address": "Borgo San Jacopo 14"},
            {"name": "Villa Cora", "address": "Viale Machiavelli 18"},
            {"name": "Belmond Villa San Michele", "address": "Via Doccia 4, Fiesole"},
            {
                "name": "J.K. Place Firenze",
                "address": "Piazza di Santa Maria Novella 7",
            },
        ],
        "restaurants": [
            {"name": "Enoteca Pinchiorri", "address": "Via Ghibellina 87"},
            {"name": "Osteria Gucci", "address": "Piazza della Signoria 10"},
            {"name": "La Leggenda dei Frati", "address": "Costa San Giorgio 6a"},
            {"name": "Trattoria Mario", "address": "Via Rosina 2r"},
            {"name": "All'Antico Vinaio", "address": "Via dei Neri 74r"},
            {"name": "Il Santo Bevitore", "address": "Via Santo Spirito 64r"},
        ],
        "attractions": [
            {"name": "Galleria degli Uffizi", "address": "Piazzale degli Uffizi 6"},
            {
                "name": "Cattedrale di Santa Maria del Fiore",
                "address": "Piazza del Duomo",
            },
            {"name": "Ponte Vecchio", "address": "Ponte Vecchio"},
            {"name": "Palazzo Pitti", "address": "Piazza de' Pitti 1"},
            {"name": "Giardino di Boboli", "address": "Piazza de' Pitti 1"},
            {"name": "Galleria dell'Accademia", "address": "Via Ricasoli 58/60"},
        ],
    },
    "Venezia": {
        "hotels": [
            {
                "name": "The Gritti Palace",
                "address": "Campo Santa Maria del Giglio 2467",
            },
            {"name": "Belmond Hotel Cipriani", "address": "Giudecca 10"},
            {"name": "Aman Venice", "address": "Calle Tiepolo 1364"},
            {
                "name": "JW Marriott Venice Resort & Spa",
                "address": "Isola delle Rose, Laguna di San Marco",
            },
            {"name": "Hotel Danieli", "address": "Riva degli Schiavoni 4196"},
            {
                "name": "San Clemente Palace Kempinski Venice",
                "address": "Isola di San Clemente 1",
            },
        ],
        "restaurants": [
            {"name": "Quadri", "address": "Piazza San Marco 121"},
            {"name": "Glam", "address": "Calle Tron 1961"},
            {"name": "Osteria alle Testiere", "address": "Calle del Mondo Novo 5801"},
            {"name": "Antiche Carampane", "address": "Rio Terà de le Carampane 1911"},
            {"name": "Caffè Florian", "address": "Piazza San Marco 57"},
            {"name": "Harry's Bar", "address": "Calle Vallaresso 1323"},
        ],
        "attractions": [
            {"name": "Piazza San Marco", "address": "Piazza San Marco"},
            {"name": "Basilica di San Marco", "address": "Piazza San Marco 328"},
            {"name": "Ponte di Rialto", "address": "Sestiere San Polo"},
            {"name": "Palazzo Ducale", "address": "Piazza San Marco 1"},
            {"name": "Canal Grande", "address": "Canal Grande"},
            {"name": "Ponte dei Sospiri", "address": "Piazza San Marco 1"},
        ],
    },
    "Napoli": {
        "hotels": [
            {"name": "Grand Hotel Vesuvio", "address": "Via Partenope 45"},
            {"name": "Romeo Hotel", "address": "Via Cristoforo Colombo 45"},
            {
                "name": "San Francesco al Monte",
                "address": "Corso Vittorio Emanuele 328",
            },
            {"name": "Grand Hotel Parker's", "address": "Corso Vittorio Emanuele 135"},
            {
                "name": "The Britannique Hotel Naples",
                "address": "Corso Vittorio Emanuele 133",
            },
            {
                "name": "Costantinopoli 104",
                "address": "Via Santa Maria di Costantinopoli 104",
            },
        ],
        "restaurants": [
            {"name": "L'Antica Pizzeria da Michele", "address": "Via Cesare Sersale 1"},
            {"name": "50 Kalò", "address": "Piazza Sannazaro 201/c"},
            {"name": "Gino e Toto Sorbillo", "address": "Via dei Tribunali 32"},
            {
                "name": "Pizzeria La Notizia 94",
                "address": "Via Michelangelo da Caravaggio 94",
            },
            {
                "name": "Palazzo Petrucci Pizzeria",
                "address": "Piazza San Domenico Maggiore 4",
            },
            {"name": "Tandem Ragù", "address": "Via Paladino 51"},
        ],
        "attractions": [
            {
                "name": "Museo Archeologico Nazionale di Napoli",
                "address": "Piazza Museo 19",
            },
            {"name": "Napoli Sotterranea", "address": "Piazza San Gaetano 68"},
            {"name": "Castel dell'Ovo", "address": "Via Eldorado 3"},
            {"name": "Cappella Sansevero", "address": "Via Francesco de Sanctis 19/21"},
            {"name": "Teatro di San Carlo", "address": "Via San Carlo 98/F"},
            {"name": "Pompei", "address": "Parco Archeologico di Pompei"},
        ],
    },
}

ITALIAN_CITIES = list(PLACES.keys())


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Trip"

    author = factory.SubFactory(UserFactory)
    title = factory.LazyAttribute(lambda obj: f"Trip to {obj.destination}")
    description = factory.Faker("sentence", nb_words=10)
    destination = factory.LazyAttribute(lambda obj: random.choice(ITALIAN_CITIES))
    start_date = factory.Faker("date_between", start_date="today", end_date="+3d")
    end_date = factory.Faker("date_between", start_date="+4d", end_date="+10d")


class LinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Link"

    author = factory.SubFactory(UserFactory)
    url = factory.Faker("url")
    title = factory.Faker("sentence")


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Event"

    class Params:
        location = factory.Faker("local_latlng", country_code="IT")
        trip = factory.SubFactory(TripFactory)
        trip_destination = random.choice(ITALIAN_CITIES)

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    trip = factory.LazyAttribute(lambda obj: obj.trip)
    name = factory.Faker("company", locale="it_IT")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["attractions"])[
            "address"
        ]
    )
    category = factory.Faker("random_element", elements=[1, 2, 3])
    website = factory.Faker("url")
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )


class TransportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Transport"

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.Faker("company", locale="it_IT")
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.Faker("address", locale="it_IT")
    destination = factory.Faker("address", locale="it_IT")
    type = factory.Faker("random_element", elements=[1, 2, 3, 4, 5, 6, 7])
    category = 1
    website = factory.Maybe(factory.Faker("pybool"), factory.Faker("url"), "")
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )


class ExperienceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Experience"

    class Params:
        trip_destination = factory.LazyAttribute(
            lambda obj: obj.day.trip.destination
            if obj.day
            else random.choice(ITALIAN_CITIES)
        )

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["attractions"])["name"]
    )
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["attractions"])[
            "address"
        ]
    )
    type = factory.Faker("random_element", elements=[1, 2, 3, 4, 5])
    category = 2
    website = factory.Maybe(factory.Faker("pybool"), factory.Faker("url"), "")
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )


class MealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Meal"

    class Params:
        trip_destination = factory.LazyAttribute(
            lambda obj: obj.day.trip.destination
            if obj.day
            else random.choice(ITALIAN_CITIES)
        )

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["restaurants"])["name"]
    )
    start_time = factory.Faker("time")
    end_time = factory.Faker("time")
    address = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["restaurants"])[
            "address"
        ]
    )
    type = factory.Faker("random_element", elements=[1, 2, 3, 4])
    category = 3
    website = factory.Maybe(factory.Faker("pybool"), factory.Faker("url"), "")
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )


class StayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Stay"

    class Params:
        day = None
        trip_destination = factory.LazyAttribute(
            lambda o: o.day.trip.destination
            if o.day
            else (
                o.trip.destination
                if hasattr(o, "trip") and o.trip
                else random.choice(ITALIAN_CITIES)
            )
        )

    name = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["hotels"])["name"]
    )
    check_in = factory.Faker("time")
    check_out = factory.Faker("time")
    cancellation_date = factory.Faker("future_date")
    phone_number = factory.Faker("phone_number", locale="it_IT")
    website = factory.Maybe(factory.Faker("pybool"), factory.Faker("url"), "")
    address = factory.LazyAttribute(
        lambda obj: random.choice(PLACES[obj.trip_destination]["hotels"])["address"]
    )
    city = factory.LazyAttribute(lambda obj: obj.trip_destination)
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )
