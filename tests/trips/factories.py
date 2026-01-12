import random
from datetime import time

import factory

from tests.accounts.factories import UserFactory

PLACES = {
    "Roma": {
        "hotels": [
            {
                "name": "Hotel Splendide Royal",
                "address": "Via di Porta Pinciana 14",
                "latitude": 41.907498,
                "longitude": 12.486339,
            },
            {
                "name": "The St. Regis Rome",
                "address": "Via Vittorio E. Orlando 3",
                "latitude": 41.90421,
                "longitude": 12.49509,
            },
            {
                "name": "Hotel Eden",
                "address": "Via Ludovisi 49",
                "latitude": 41.906582,
                "longitude": 12.486484,
            },
            {
                "name": "Hotel Palazzo Manfredi",
                "address": "Via Labicana 125",
                "latitude": 41.890189,
                "longitude": 12.4956,
            },
            {
                "name": "Villa Spalletti Trivelli",
                "address": "Via Piacenza 4",
                "latitude": 41.899278,
                "longitude": 12.488457,
            },
            {
                "name": "Anantara Palazzo Naiadi Hotel",
                "address": "Piazza della Repubblica 48",
                "latitude": 41.902483,
                "longitude": 12.496143,
            },
        ],
        "restaurants": [
            {
                "name": "La Pergola",
                "address": "Via Alberto Cadlolo 101",
                "latitude": 41.919265,
                "longitude": 12.445843,
            },
            {
                "name": "Il Pagliaccio",
                "address": "Via dei Banchi Vecchi 129a",
                "latitude": 41.897819,
                "longitude": 12.467488,
            },
            {
                "name": "Roscioli Salumeria con Cucina",
                "address": "Via dei Giubbonari 21",
                "latitude": 41.89422,
                "longitude": 12.47426,
            },
            {
                "name": "Armando al Pantheon",
                "address": "Salita de' Crescenzi 31",
                "latitude": 41.899051,
                "longitude": 12.476223,
            },
            {
                "name": "Trattoria da Cesare",
                "address": "Via del Casaletto 45",
                "latitude": 41.877306,
                "longitude": 12.44062,
            },
            {
                "name": "Trattoria Monti",
                "address": "Via di S. Vito 13",
                "latitude": 41.895939,
                "longitude": 12.501484,
            },
        ],
        "attractions": [
            {
                "name": "Colosseo",
                "address": "Piazza del Colosseo 1",
                "latitude": 41.889955,
                "longitude": 12.49427,
            },
            {
                "name": "Foro Romano",
                "address": "Largo della Salara Vecchia 5/6",
                "latitude": 41.89298,
                "longitude": 12.487015,
            },
            {
                "name": "Pantheon",
                "address": "Piazza della Rotonda",
                "latitude": 41.899065,
                "longitude": 12.477139,
            },
            {
                "name": "Fontana di Trevi",
                "address": "Piazza di Trevi",
                "latitude": 41.900775,
                "longitude": 12.483287,
            },
            {
                "name": "Musei Vaticani",
                "address": "Viale Vaticano",
                "latitude": 41.904063,
                "longitude": 12.448593,
            },
            {
                "name": "Castel Sant'Angelo",
                "address": "Lungotevere Castello, 50",
                "latitude": 41.903065,
                "longitude": 12.466276,
            },
        ],
    },
    "Milano": {
        "hotels": [
            {
                "name": "Bulgari Hotel Milano",
                "address": "Via Privata Fratelli Gabba 7b",
                "latitude": 45.470338,
                "longitude": 9.189774,
            },
            {
                "name": "Armani Hotel Milano",
                "address": "Via Alessandro Manzoni 31",
                "latitude": 45.470575,
                "longitude": 9.193112,
            },
            {
                "name": "Park Hyatt Milano",
                "address": "Via Tommaso Grossi 1",
                "latitude": 45.465457,
                "longitude": 9.188786,
            },
            {
                "name": "Grand Hotel et de Milan",
                "address": "Via Manzoni 29",
                "latitude": 45.469936,
                "longitude": 9.192522,
            },
            {
                "name": "Palazzo Parigi Hotel & Grand Spa",
                "address": "Corso di Porta Nuova 1",
                "latitude": 45.473401,
                "longitude": 9.191131,
            },
            {
                "name": "Four Seasons Hotel Milano",
                "address": "Via Gesu 6/8",
                "latitude": 45.377415,
                "longitude": 9.217151,
            },
        ],
        "restaurants": [
            {
                "name": "Enrico Bartolini al MUDEC",
                "address": "Via Tortona 56",
                "latitude": 45.451548,
                "longitude": 9.161626,
            },
            {
                "name": "Seta by Antonio Guida",
                "address": "Via Andegari 9",
                "latitude": 45.46925,
                "longitude": 9.19092,
            },
            {
                "name": "Cracco",
                "address": "Galleria Vittorio Emanuele II",
                "latitude": 45.465599,
                "longitude": 9.190020,
            },
            {
                "name": "Il Luogo di Aimo e Nadia",
                "address": "Via Privata Raimondo Montecuccoli 6",
                "latitude": 45.458420,
                "longitude": 9.131080,
            },
            {
                "name": "Trippa Milano",
                "address": "Via Giorgio Vasari 1",
                "latitude": 45.451992,
                "longitude": 9.205444,
            },
            {
                "name": "Ratanà",
                "address": "Via Gaetano de Castillia 28",
                "latitude": 45.485738,
                "longitude": 9.192806,
            },
        ],
        "attractions": [
            {
                "name": "Duomo di Milano",
                "address": "Piazza del Duomo",
                "latitude": 45.464678,
                "longitude": 9.190544,
            },
            {
                "name": "Galleria Vittorio Emanuele II",
                "address": "Piazza del Duomo",
                "latitude": 45.464678,
                "longitude": 9.190544,
            },
            {
                "name": "Teatro alla Scala",
                "address": "Via Filodrammatici 2",
                "latitude": 45.467282,
                "longitude": 9.188828,
            },
            {
                "name": "Basilica di Sant'Ambrogio",
                "address": "Piazza Sant'Ambrogio, 15",
                "latitude": 45.462506,
                "longitude": 9.175612,
            },
            {
                "name": "Pinacoteca di Brera",
                "address": "Via Brera 28",
                "latitude": 45.472127,
                "longitude": 9.187651,
            },
            {
                "name": "Santa Maria delle Grazie",
                "address": "Piazza di Santa Maria delle Grazie",
                "latitude": 45.465972,
                "longitude": 9.171139,
            },
        ],
    },
    "Firenze": {
        "hotels": [
            {
                "name": "Four Seasons Hotel Firenze",
                "address": "Borgo Pinti 99",
                "latitude": 43.776021,
                "longitude": 11.265569,
            },
            {
                "name": "The St. Regis Florence",
                "address": "Piazza Ognissanti 1",
                "latitude": 43.772252,
                "longitude": 11.245197,
            },
            {
                "name": "Hotel Lungarno",
                "address": "Borgo San Jacopo 14",
                "latitude": 43.767972,
                "longitude": 11.251542,
            },
            {
                "name": "Villa Cora",
                "address": "Viale Machiavelli 18",
                "latitude": 43.756809,
                "longitude": 11.247376,
            },
            {
                "name": "Belmond Villa San Michele",
                "address": "Via Doccia 4, Fiesole",
                "latitude": 43.802749,
                "longitude": 11.298126,
            },
            {
                "name": "J.K. Place Firenze",
                "address": "Piazza di Santa Maria Novella 7",
                "latitude": 43.773017,
                "longitude": 11.24977,
            },
        ],
        "restaurants": [
            {
                "name": "Enoteca Pinchiorri",
                "address": "Via Ghibellina 87",
                "latitude": 43.770031,
                "longitude": 11.262322,
            },
            {
                "name": "Osteria Gucci",
                "address": "Piazza della Signoria 10",
                "latitude": 43.769772,
                "longitude": 11.255179,
            },
            {
                "name": "La Leggenda dei Frati",
                "address": "Costa San Giorgio 6a",
                "latitude": 43.764322,
                "longitude": 11.256039,
            },
            {
                "name": "Trattoria Mario",
                "address": "Via Rosina 2r",
                "latitude": 43.776569,
                "longitude": 11.254534,
            },
            {
                "name": "All'Antico Vinaio",
                "address": "Via dei Neri 74r",
                "latitude": 43.768477,
                "longitude": 11.257417,
            },
            {
                "name": "Il Santo Bevitore",
                "address": "Via Santo Spirito 64r",
                "latitude": 43.769025,
                "longitude": 11.246808,
            },
        ],
        "attractions": [
            {
                "name": "Galleria degli Uffizi",
                "address": "Piazzale degli Uffizi 6",
                "latitude": 43.768997,
                "longitude": 11.255814,
            },
            {
                "name": "Cattedrale di Santa Maria del Fiore",
                "address": "Piazza del Duomo",
                "latitude": 43.773455,
                "longitude": 11.256592,
            },
            {
                "name": "Ponte Vecchio",
                "address": "Ponte Vecchio",
                "latitude": 43.768009,
                "longitude": 11.253165,
            },
            {
                "name": "Palazzo Pitti",
                "address": "Piazza de' Pitti 1",
                "latitude": 43.765239,
                "longitude": 11.248344,
            },
            {
                "name": "Giardino di Boboli",
                "address": "Piazza de' Pitti 1",
                "latitude": 43.765239,
                "longitude": 11.248344,
            },
            {
                "name": "Galleria dell'Accademia",
                "address": "Via Ricasoli 58/60",
                "latitude": 43.77545,
                "longitude": 11.257513,
            },
        ],
    },
    "Venezia": {
        "hotels": [
            {
                "name": "The Gritti Palace",
                "address": "Campo Santa Maria del Giglio 2467",
                "latitude": 45.4325,
                "longitude": 12.3328,
            },
            {
                "name": "Belmond Hotel Cipriani",
                "address": "Giudecca 10",
                "latitude": 45.427526,
                "longitude": 12.34029,
            },
            {
                "name": "Aman Venice",
                "address": "Calle Tiepolo 1364",
                "latitude": 45.436965,
                "longitude": 12.331469,
            },
            {
                "name": "JW Marriott Venice Resort & Spa",
                "address": "Isola delle Rose, Laguna di San Marco",
                "latitude": 45.436974,
                "longitude": 12.336337,
            },
            {
                "name": "Hotel Danieli",
                "address": "Riva degli Schiavoni 4196",
                "latitude": 45.433868,
                "longitude": 12.342064,
            },
            {
                "name": "San Clemente Palace Kempinski Venice",
                "address": "Isola di San Clemente 1",
                "latitude": 45.436974,
                "longitude": 12.336337,
            },
        ],
        "restaurants": [
            {
                "name": "Quadri",
                "address": "Piazza San Marco 121",
                "latitude": 45.434334,
                "longitude": 12.338031,
            },
            {
                "name": "Glam",
                "address": "Calle Tron 1961",
                "latitude": 45.441279,
                "longitude": 12.329806,
            },
            {
                "name": "Osteria alle Testiere",
                "address": "Calle del Mondo Novo 5801",
                "latitude": 45.43706,
                "longitude": 12.340151,
            },
            {
                "name": "Antiche Carampane",
                "address": "Rio Terà de le Carampane 1911",
                "latitude": 45.438559,
                "longitude": 12.331381,
            },
            {
                "name": "Caffè Florian",
                "address": "Piazza San Marco 57",
                "latitude": 45.433617,
                "longitude": 12.338275,
            },
            {
                "name": "Harry's Bar",
                "address": "Calle Vallaresso 1323",
                "latitude": 45.432405,
                "longitude": 12.337259,
            },
        ],
        "attractions": [
            {
                "name": "Piazza San Marco",
                "address": "Piazza San Marco",
                "latitude": 45.429447,
                "longitude": 12.344971,
            },
            {
                "name": "Basilica di San Marco",
                "address": "Piazza San Marco 328",
                "latitude": 45.434233,
                "longitude": 12.338073,
            },
            {
                "name": "Ponte di Rialto",
                "address": "Sestiere San Polo",
                "latitude": 45.438069,
                "longitude": 12.33566,
            },
            {
                "name": "Palazzo Ducale",
                "address": "Piazza San Marco 1",
                "latitude": 45.433628,
                "longitude": 12.339639,
            },
            {
                "name": "Canal Grande",
                "address": "Canal Grande",
                "latitude": 45.436974,
                "longitude": 12.336337,
            },
            {
                "name": "Ponte dei Sospiri",
                "address": "Piazza San Marco 1",
                "latitude": 45.433628,
                "longitude": 12.339639,
            },
        ],
    },
    "Napoli": {
        "hotels": [
            {
                "name": "Grand Hotel Vesuvio",
                "address": "Via Partenope 45",
                "latitude": 40.829939,
                "longitude": 14.24788,
            },
            {
                "name": "Romeo Hotel",
                "address": "Via Cristoforo Colombo 45",
                "latitude": 40.840586,
                "longitude": 14.255911,
            },
            {
                "name": "San Francesco al Monte",
                "address": "Corso Vittorio Emanuele 328",
                "latitude": 40.915125,
                "longitude": 14.406373,
            },
            {
                "name": "Grand Hotel Parker's",
                "address": "Corso Vittorio Emanuele 135",
                "latitude": 40.836755,
                "longitude": 14.22961,
            },
            {
                "name": "The Britannique Hotel Naples",
                "address": "Corso Vittorio Emanuele 133",
                "latitude": 40.836855,
                "longitude": 14.22946,
            },
            {
                "name": "Costantinopoli 104",
                "address": "Via Santa Maria di Costantinopoli 104",
                "latitude": 40.850881,
                "longitude": 14.251795,
            },
        ],
        "restaurants": [
            {
                "name": "L'Antica Pizzeria da Michele",
                "address": "Via Cesare Sersale 1",
                "latitude": 40.849749,
                "longitude": 14.263352,
            },
            {
                "name": "50 Kalò",
                "address": "Piazza Sannazaro 201/c",
                "latitude": 40.84603,
                "longitude": 14.253269,
            },
            {
                "name": "Gino e Toto Sorbillo",
                "address": "Via dei Tribunali 32",
                "latitude": 40.850388,
                "longitude": 14.25534,
            },
            {
                "name": "Pizzeria La Notizia 94",
                "address": "Via Michelangelo da Caravaggio 94",
                "latitude": 40.907356,
                "longitude": 14.276228,
            },
            {
                "name": "Palazzo Petrucci Pizzeria",
                "address": "Piazza San Domenico Maggiore 4",
                "latitude": 40.849369,
                "longitude": 14.254302,
            },
            {
                "name": "Tandem Ragù",
                "address": "Via Paladino 51",
                "latitude": 40.821745,
                "longitude": 14.330889,
            },
        ],
        "attractions": [
            {
                "name": "Museo Archeologico Nazionale di Napoli",
                "address": "Piazza Museo 19",
                "latitude": 40.852929,
                "longitude": 14.250119,
            },
            {
                "name": "Napoli Sotterranea",
                "address": "Piazza San Gaetano 68",
                "latitude": 40.851138,
                "longitude": 14.256786,
            },
            {
                "name": "Castel dell'Ovo",
                "address": "Via Eldorado 3",
                "latitude": 40.828481,
                "longitude": 14.247945,
            },
            {
                "name": "Cappella Sansevero",
                "address": "Via Francesco de Sanctis 19/21",
                "latitude": 40.955559,
                "longitude": 14.31018,
            },
            {
                "name": "Teatro di San Carlo",
                "address": "Via San Carlo 98/F",
                "latitude": 40.838071,
                "longitude": 14.250209,
            },
            {
                "name": "Pompei",
                "address": "Parco Archeologico di Pompei",
                "latitude": 40.749256,
                "longitude": 14.493669,
            },
        ],
    },
}

ITALIAN_CITIES = list(PLACES.keys())

TRANSPORT_DESTINATIONS = {
    "Roma": ["Frascati", "Tivoli", "Ostia", "Civitavecchia"],
    "Milano": ["Monza", "Como", "Pavia", "Bergamo"],
    "Firenze": ["Prato", "Sesto Fiorentino", "Empoli", "Fiesole"],
    "Venezia": ["Mestre", "Chioggia", "Jesolo", "Mogliano Veneto"],
    "Napoli": ["Pozzuoli", "Ercolano", "Pompei", "Sorrento"],
}

# MainTransfer locations (airports and stations for each city in PLACES)
MAIN_TRANSFER_LOCATIONS = {
    "Roma": {
        "airports": [
            {
                "name": "Leonardo da Vinci–Fiumicino Airport",
                "code": "FCO",
                "address": "Via dell'Aeroporto di Fiumicino",
                "latitude": 41.8002778,
                "longitude": 12.2388889,
            },
            {
                "name": "Ciampino–G. B. Pastine International Airport",
                "code": "CIA",
                "address": "Via Appia Nuova 1651",
                "latitude": 41.7994,
                "longitude": 12.5949,
            },
        ],
        "stations": [
            {
                "name": "Roma Termini",
                "code": "RMT",
                "address": "Piazza dei Cinquecento",
                "latitude": 41.9009,
                "longitude": 12.5028,
            },
            {
                "name": "Roma Tiburtina",
                "code": "RTI",
                "address": "Piazzale della Stazione Tiburtina",
                "latitude": 41.9099,
                "longitude": 12.5316,
            },
        ],
    },
    "Milano": {
        "airports": [
            {
                "name": "Malpensa International Airport",
                "code": "MXP",
                "address": "Via Aeroporto",
                "latitude": 45.6306,
                "longitude": 8.72811,
            },
            {
                "name": "Milano Linate Airport",
                "code": "LIN",
                "address": "Viale Enrico Forlanini",
                "latitude": 45.445099,
                "longitude": 9.27674,
            },
        ],
        "stations": [
            {
                "name": "Milano Centrale",
                "code": "MIL",
                "address": "Piazza Duca d'Aosta 1",
                "latitude": 45.4842,
                "longitude": 9.2040,
            },
            {
                "name": "Milano Porta Garibaldi",
                "code": "MIG",
                "address": "Piazza Freud",
                "latitude": 45.4858,
                "longitude": 9.1879,
            },
        ],
    },
    "Firenze": {
        "airports": [
            {
                "name": "Peretola Airport",
                "code": "FLR",
                "address": "Via del Termine 11",
                "latitude": 43.810001,
                "longitude": 11.2051,
            },
        ],
        "stations": [
            {
                "name": "Firenze Santa Maria Novella",
                "code": "FIR",
                "address": "Piazza della Stazione",
                "latitude": 43.7766,
                "longitude": 11.2478,
            },
            {
                "name": "Firenze Campo di Marte",
                "code": "FCM",
                "address": "Viale Fanti",
                "latitude": 43.7814,
                "longitude": 11.2827,
            },
        ],
    },
    "Venezia": {
        "airports": [
            {
                "name": "Venice Marco Polo Airport",
                "code": "VCE",
                "address": "Viale Galileo Galilei 30/1",
                "latitude": 45.505299,
                "longitude": 12.3519,
            },
        ],
        "stations": [
            {
                "name": "Venezia Santa Lucia",
                "code": "VEN",
                "address": "Fondamenta Santa Lucia",
                "latitude": 45.4410,
                "longitude": 12.3207,
            },
            {
                "name": "Venezia Mestre",
                "code": "VEM",
                "address": "Piazzale Favretti",
                "latitude": 45.4786,
                "longitude": 12.2329,
            },
        ],
    },
    "Napoli": {
        "airports": [
            {
                "name": "Naples International Airport",
                "code": "NAP",
                "address": "Viale Umberto Maddalena",
                "latitude": 40.886002,
                "longitude": 14.2908,
            },
        ],
        "stations": [
            {
                "name": "Napoli Centrale",
                "code": "NAC",
                "address": "Piazza Garibaldi",
                "latitude": 40.8530,
                "longitude": 14.2738,
            },
            {
                "name": "Napoli Mergellina",
                "code": "NAM",
                "address": "Via Mergellina",
                "latitude": 40.8270,
                "longitude": 14.2145,
            },
        ],
    },
    # Bologna - external city for MainTransfers origin/destination
    "Bologna": {
        "airports": [
            {
                "name": "Bologna Guglielmo Marconi Airport",
                "code": "BLQ",
                "address": "Via del Triumvirato 84",
                "latitude": 44.5354,
                "longitude": 11.2887,
            },
        ],
        "stations": [
            {
                "name": "Bologna Centrale",
                "code": "BOL",
                "address": "Piazza delle Medaglie d'Oro",
                "latitude": 44.493681,
                "longitude": 11.343169,
            },
        ],
    },
}


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Trip"

    author = factory.SubFactory(UserFactory)
    title = factory.LazyAttribute(
        lambda obj: random.choice(
            [
                f"Gita a {obj.destination}",
                obj.destination,
                f"Vacanze in {obj.destination}",
                "Vacanze di Pasqua",
                "Viaggio di Nozze 2026",
            ]
        )
    )
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
        exclude = ("chosen_place",)

    class Params:
        trip = factory.SubFactory(TripFactory)
        chosen_place = factory.LazyAttribute(
            lambda o: random.choice(
                PLACES[o.trip.destination]["attractions"]
                + PLACES[o.trip.destination]["restaurants"]
            )
        )

    trip = factory.SelfAttribute("trip")
    day = factory.LazyAttribute(lambda o: random.choice(o.trip.days.all()))
    city = factory.LazyAttribute(lambda o: o.trip.destination)
    name = factory.LazyAttribute(lambda o: o.chosen_place["name"])
    address = factory.LazyAttribute(lambda o: o.chosen_place["address"])
    latitude = factory.LazyAttribute(lambda o: o.chosen_place.get("latitude"))
    longitude = factory.LazyAttribute(lambda o: o.chosen_place.get("longitude"))
    start_time = factory.LazyFunction(lambda: time(10, 0))
    end_time = factory.LazyFunction(lambda: time(11, 0))
    website = factory.Faker("url")
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )


class TransportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Transport"

    class Params:
        trip_destination = factory.LazyAttribute(
            lambda obj: obj.day.trip.destination
            if obj.day
            else random.choice(ITALIAN_CITIES)
        )
        origin_details = factory.LazyAttribute(
            lambda obj: random.choice(PLACES[obj.trip_destination]["hotels"])
        )
        destination_details = factory.LazyAttribute(
            lambda obj: random.choice(PLACES[obj.trip_destination]["attractions"])
        )

    day = factory.LazyAttribute(lambda obj: obj.trip.days.order_by("?").first())
    name = factory.Faker("city", locale="it_IT")
    start_time = factory.LazyFunction(lambda: time(10, 0))
    end_time = factory.LazyFunction(lambda: time(11, 0))

    # Parent Event fields (still needed for compatibility)
    address = factory.LazyAttribute(lambda obj: obj.origin_details["address"])
    latitude = factory.LazyAttribute(lambda obj: obj.origin_details.get("latitude"))
    longitude = factory.LazyAttribute(lambda obj: obj.origin_details.get("longitude"))

    # Origin fields
    origin_city = factory.LazyAttribute(lambda obj: obj.trip_destination)
    origin_address = factory.LazyAttribute(lambda obj: obj.origin_details["address"])
    origin_latitude = factory.LazyAttribute(
        lambda obj: obj.origin_details.get("latitude")
    )
    origin_longitude = factory.LazyAttribute(
        lambda obj: obj.origin_details.get("longitude")
    )

    # Destination fields
    destination_city = factory.LazyAttribute(
        lambda obj: random.choice(TRANSPORT_DESTINATIONS[obj.trip_destination])
    )
    destination_address = factory.LazyAttribute(
        lambda obj: obj.destination_details["address"]
    )
    destination_latitude = factory.LazyAttribute(
        lambda obj: obj.destination_details.get("latitude")
    )
    destination_longitude = factory.LazyAttribute(
        lambda obj: obj.destination_details.get("longitude")
    )

    # Booking fields
    booking_reference = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("bothify", text="??#####"),
        "",
    )
    company = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("company", locale="it_IT"),
        "",
    )
    ticket_url = factory.Maybe(factory.Faker("pybool"), factory.Faker("url"), "")
    price = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True),
        None,
    )

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
        exclude = ("chosen_place",)

    class Params:
        trip = factory.SubFactory(TripFactory)
        chosen_place = factory.LazyAttribute(
            lambda o: random.choice(PLACES[o.trip.destination]["attractions"])
        )

    trip = factory.SelfAttribute("trip")
    day = factory.LazyAttribute(lambda o: random.choice(o.trip.days.all()))
    city = factory.LazyAttribute(lambda o: o.trip.destination)
    name = factory.LazyAttribute(lambda o: o.chosen_place["name"])
    address = factory.LazyAttribute(lambda o: o.chosen_place["address"])
    latitude = factory.LazyAttribute(lambda o: o.chosen_place.get("latitude"))
    longitude = factory.LazyAttribute(lambda o: o.chosen_place.get("longitude"))
    start_time = factory.LazyFunction(lambda: time(10, 0))
    end_time = factory.LazyFunction(lambda: time(11, 0))
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
        exclude = ("chosen_place",)

    class Params:
        trip = factory.SubFactory(TripFactory)
        chosen_place = factory.LazyAttribute(
            lambda o: random.choice(PLACES[o.trip.destination]["restaurants"])
        )

    trip = factory.SelfAttribute("trip")
    day = factory.LazyAttribute(lambda o: random.choice(o.trip.days.all()))
    city = factory.LazyAttribute(lambda o: o.trip.destination)
    name = factory.LazyAttribute(lambda o: o.chosen_place["name"])
    address = factory.LazyAttribute(lambda o: o.chosen_place["address"])
    latitude = factory.LazyAttribute(lambda o: o.chosen_place.get("latitude"))
    longitude = factory.LazyAttribute(lambda o: o.chosen_place.get("longitude"))
    start_time = factory.LazyFunction(lambda: time(10, 0))
    end_time = factory.LazyFunction(lambda: time(11, 0))
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
        exclude = ("chosen_place",)
        skip_postgeneration_save = True

    class Params:
        chosen_place = factory.LazyAttribute(
            lambda o: random.choice(PLACES[o.city]["hotels"])
        )

    city = factory.LazyFunction(lambda: random.choice(ITALIAN_CITIES))
    name = factory.LazyAttribute(lambda o: o.chosen_place["name"])
    address = factory.LazyAttribute(lambda o: o.chosen_place["address"])
    latitude = factory.LazyAttribute(lambda o: o.chosen_place.get("latitude"))
    longitude = factory.LazyAttribute(lambda o: o.chosen_place.get("longitude"))
    check_in = factory.LazyFunction(
        lambda: f"{random.randint(12, 15):02d}:{random.choice([0, 30]):02d}"
    )
    check_out = factory.LazyFunction(
        lambda: f"{random.randint(7, 11):02d}:{random.choice([0, 30]):02d}"
    )
    cancellation_date = factory.Faker("future_date")
    phone_number = factory.Faker("phone_number", locale="it_IT")
    website = factory.Maybe(factory.Faker("pybool"), factory.Faker("url"), "")
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=8),
        "",
    )

    @factory.post_generation
    def day(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            extracted.stay = self
            extracted.save()


class MainTransferFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.MainTransfer"
        exclude = ("origin_place", "destination_place")

    trip = factory.SubFactory(TripFactory)
    type = factory.Faker(
        "random_element", elements=[1, 2, 3, 4]
    )  # PLANE, TRAIN, CAR, OTHER
    direction = factory.Faker("random_element", elements=[1, 2])  # ARRIVAL or DEPARTURE

    class Params:
        # For ARRIVAL: origin from Bologna, destination in trip city
        # For DEPARTURE: origin from trip city, destination in Bologna
        origin_place = factory.LazyAttribute(
            lambda o: random.choice(
                MAIN_TRANSFER_LOCATIONS["Bologna"]["airports"]
                if o.type == 1
                else MAIN_TRANSFER_LOCATIONS["Bologna"]["stations"]
                if o.type == 2
                else MAIN_TRANSFER_LOCATIONS["Bologna"]["airports"]
                + MAIN_TRANSFER_LOCATIONS["Bologna"]["stations"]
            )
            if o.direction == 1
            else random.choice(
                MAIN_TRANSFER_LOCATIONS[o.trip.destination]["airports"]
                if o.type == 1
                else MAIN_TRANSFER_LOCATIONS[o.trip.destination]["stations"]
                if o.type == 2
                else MAIN_TRANSFER_LOCATIONS[o.trip.destination]["airports"]
                + MAIN_TRANSFER_LOCATIONS[o.trip.destination]["stations"]
            )
        )
        destination_place = factory.LazyAttribute(
            lambda o: random.choice(
                MAIN_TRANSFER_LOCATIONS[o.trip.destination]["airports"]
                if o.type == 1
                else MAIN_TRANSFER_LOCATIONS[o.trip.destination]["stations"]
                if o.type == 2
                else MAIN_TRANSFER_LOCATIONS[o.trip.destination]["airports"]
                + MAIN_TRANSFER_LOCATIONS[o.trip.destination]["stations"]
            )
            if o.direction == 1
            else random.choice(
                MAIN_TRANSFER_LOCATIONS["Bologna"]["airports"]
                if o.type == 1
                else MAIN_TRANSFER_LOCATIONS["Bologna"]["stations"]
                if o.type == 2
                else MAIN_TRANSFER_LOCATIONS["Bologna"]["airports"]
                + MAIN_TRANSFER_LOCATIONS["Bologna"]["stations"]
            )
        )

    # Origin fields
    origin_name = factory.LazyAttribute(lambda o: o.origin_place["name"])
    origin_code = factory.LazyAttribute(lambda o: o.origin_place["code"])
    origin_address = factory.LazyAttribute(lambda o: o.origin_place["address"])
    origin_latitude = factory.LazyAttribute(lambda o: o.origin_place["latitude"])
    origin_longitude = factory.LazyAttribute(lambda o: o.origin_place["longitude"])

    # Destination fields
    destination_name = factory.LazyAttribute(lambda o: o.destination_place["name"])
    destination_code = factory.LazyAttribute(lambda o: o.destination_place["code"])
    destination_address = factory.LazyAttribute(
        lambda o: o.destination_place["address"]
    )
    destination_latitude = factory.LazyAttribute(
        lambda o: o.destination_place["latitude"]
    )
    destination_longitude = factory.LazyAttribute(
        lambda o: o.destination_place["longitude"]
    )

    # Time fields
    start_time = factory.LazyFunction(lambda: time(10, 0))
    end_time = factory.LazyFunction(lambda: time(12, 0))

    # Optional fields
    booking_reference = factory.Faker("bothify", text="??#####")
    ticket_url = factory.Faker("url")
    notes = ""
    type_specific_data = factory.LazyFunction(dict)


class SimpleTransferFactory(factory.django.DjangoModelFactory):
    """Factory for SimpleTransfer (transfers between events on same day)"""

    class Meta:
        model = "trips.SimpleTransfer"

    # Create two events on same day for testing
    from_event = factory.SubFactory(ExperienceFactory)
    to_event = factory.SubFactory(
        ExperienceFactory,
        trip=factory.SelfAttribute("..from_event.trip"),
        day=factory.SelfAttribute("..from_event.day"),
    )

    # Auto-populated from events (will be set in save())
    day = factory.SelfAttribute("from_event.day")
    trip = factory.SelfAttribute("from_event.trip")

    # Transfer details
    transport_mode = factory.Faker(
        "random_element", elements=["car", "train", "walk", "bus", "taxi"]
    )
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=6),
        "",
    )

    # Optional time fields
    departure_time = None
    estimated_duration = None


class StayTransferFactory(factory.django.DjangoModelFactory):
    """Factory for StayTransfer (transfers between stays on consecutive days)"""

    class Meta:
        model = "trips.StayTransfer"

    class Params:
        # Create trip with consecutive days having different stays
        trip = factory.SubFactory(TripFactory)

    # Create two different stays
    from_stay = factory.SubFactory(StayFactory)
    to_stay = factory.SubFactory(StayFactory)

    # Days must be consecutive (will be set via post_generation)
    from_day = None
    to_day = None
    trip = factory.SelfAttribute("from_day.trip")

    # Transfer details
    transport_mode = factory.Faker(
        "random_element", elements=["car", "train", "plane", "bus"]
    )
    notes = factory.Maybe(
        factory.Faker("pybool"),
        factory.Faker("sentence", nb_words=6),
        "",
    )

    # Optional time fields
    departure_time = None
    estimated_duration = None
