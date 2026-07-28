import random
from datetime import time
from decimal import Decimal

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
            {
                "name": "Da Enzo al 29",
                "address": "Via dei Vascellari 29",
                "latitude": 41.888889,
                "longitude": 12.476944,
            },
            {
                "name": "Felice a Testaccio",
                "address": "Via Mastro Giorgio 29",
                "latitude": 41.877639,
                "longitude": 12.475556,
            },
            {
                "name": "Pierluigi",
                "address": "Piazza de' Ricci 144",
                "latitude": 41.896667,
                "longitude": 12.470556,
            },
            {
                "name": "Trattoria Pennestri",
                "address": "Via Giovanni da Empoli 5",
                "latitude": 41.873611,
                "longitude": 12.480278,
            },
            {
                "name": "Osteria Fernanda",
                "address": "Via Ettore Rolli 1",
                "latitude": 41.882778,
                "longitude": 12.469167,
            },
            {
                "name": "Flavio al Velavevodetto",
                "address": "Via di Monte Testaccio 97",
                "latitude": 41.876111,
                "longitude": 12.474722,
            },
            {
                "name": "Cesare al Casaletto",
                "address": "Via del Casaletto 45",
                "latitude": 41.877306,
                "longitude": 12.44062,
            },
            {
                "name": "Santo Palato",
                "address": "Piazza Tarquinia 4a",
                "latitude": 41.884722,
                "longitude": 12.514167,
            },
            {
                "name": "Marzapane Roma",
                "address": "Via Velletri 39",
                "latitude": 41.917222,
                "longitude": 12.501389,
            },
            {
                "name": "Pipero Roma",
                "address": "Corso Vittorio Emanuele II 250",
                "latitude": 41.898333,
                "longitude": 12.469722,
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
            {
                "name": "Galleria Borghese",
                "address": "Piazzale Scipione Borghese 5",
                "latitude": 41.914167,
                "longitude": 12.492222,
            },
            {
                "name": "Piazza Navona",
                "address": "Piazza Navona",
                "latitude": 41.899033,
                "longitude": 12.473049,
            },
            {
                "name": "Piazza di Spagna",
                "address": "Piazza di Spagna",
                "latitude": 41.905989,
                "longitude": 12.482775,
            },
            {
                "name": "Basilica di San Pietro",
                "address": "Piazza San Pietro",
                "latitude": 41.902168,
                "longitude": 12.453937,
            },
            {
                "name": "Terme di Caracalla",
                "address": "Viale delle Terme di Caracalla 52",
                "latitude": 41.879167,
                "longitude": 12.492500,
            },
            {
                "name": "Basilica di Santa Maria Maggiore",
                "address": "Piazza di Santa Maria Maggiore",
                "latitude": 41.897556,
                "longitude": 12.498500,
            },
            {
                "name": "Villa Borghese",
                "address": "Piazzale Napoleone I",
                "latitude": 41.912500,
                "longitude": 12.484722,
            },
            {
                "name": "Palatino",
                "address": "Via di San Gregorio 30",
                "latitude": 41.888611,
                "longitude": 12.487500,
            },
            {
                "name": "Trastevere",
                "address": "Piazza di Santa Maria in Trastevere",
                "latitude": 41.889444,
                "longitude": 12.469722,
            },
            {
                "name": "Bocca della Verità",
                "address": "Piazza della Bocca della Verità 18",
                "latitude": 41.888056,
                "longitude": 12.481389,
            },
            {
                "name": "Campidoglio",
                "address": "Piazza del Campidoglio",
                "latitude": 41.893333,
                "longitude": 12.482778,
            },
            {
                "name": "Musei Capitolini",
                "address": "Piazza del Campidoglio 1",
                "latitude": 41.893056,
                "longitude": 12.482500,
            },
            {
                "name": "Basilica di San Giovanni in Laterano",
                "address": "Piazza di San Giovanni in Laterano 4",
                "latitude": 41.885833,
                "longitude": 12.505833,
            },
            {
                "name": "Ara Pacis",
                "address": "Lungotevere in Augusta",
                "latitude": 41.906111,
                "longitude": 12.475278,
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
            {
                "name": "Antica Trattoria della Pesa",
                "address": "Viale Pasubio 10",
                "latitude": 45.482222,
                "longitude": 9.184722,
            },
            {
                "name": "Langosteria",
                "address": "Via Savona 10",
                "latitude": 45.455000,
                "longitude": 9.166944,
            },
            {
                "name": "Da Giacomo",
                "address": "Via Pasquale Sottocorno 6",
                "latitude": 45.468611,
                "longitude": 9.207222,
            },
            {
                "name": "Trattoria del Nuovo Macello",
                "address": "Via Cesare Lombroso 20",
                "latitude": 45.451667,
                "longitude": 9.221944,
            },
            {
                "name": "Al Pont de Ferr",
                "address": "Ripa di Porta Ticinese 55",
                "latitude": 45.451389,
                "longitude": 9.174722,
            },
            {
                "name": "Osteria del Binari",
                "address": "Via Tortona 1",
                "latitude": 45.452778,
                "longitude": 9.170278,
            },
            {
                "name": "Contraste",
                "address": "Via Giuseppe Meda 2",
                "latitude": 45.446389,
                "longitude": 9.183611,
            },
            {
                "name": "Trattoria Masuelli San Marco",
                "address": "Viale Umbria 80",
                "latitude": 45.451111,
                "longitude": 9.216944,
            },
            {
                "name": "Un Posto a Milano",
                "address": "Via Privata Cuccagna 2",
                "latitude": 45.451389,
                "longitude": 9.212778,
            },
            {
                "name": "Berberè Isola",
                "address": "Via Sebenico 21",
                "latitude": 45.489444,
                "longitude": 9.192778,
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
            {
                "name": "Castello Sforzesco",
                "address": "Piazza Castello",
                "latitude": 45.470417,
                "longitude": 9.179444,
            },
            {
                "name": "Cimitero Monumentale",
                "address": "Piazzale Cimitero Monumentale",
                "latitude": 45.486944,
                "longitude": 9.179722,
            },
            {
                "name": "Navigli",
                "address": "Naviglio Grande",
                "latitude": 45.451667,
                "longitude": 9.172778,
            },
            {
                "name": "Museo del Novecento",
                "address": "Piazza del Duomo 8",
                "latitude": 45.463056,
                "longitude": 9.190833,
            },
            {
                "name": "Fondazione Prada",
                "address": "Largo Isarco 2",
                "latitude": 45.438889,
                "longitude": 9.204722,
            },
            {
                "name": "Parco Sempione",
                "address": "Piazza Sempione",
                "latitude": 45.472500,
                "longitude": 9.176389,
            },
            {
                "name": "Cenacolo Vinciano",
                "address": "Piazza di Santa Maria delle Grazie 2",
                "latitude": 45.466111,
                "longitude": 9.170556,
            },
            {
                "name": "Arco della Pace",
                "address": "Piazza Sempione",
                "latitude": 45.475556,
                "longitude": 9.172222,
            },
            {
                "name": "Basilica di Sant'Eustorgio",
                "address": "Piazza Sant'Eustorgio 1",
                "latitude": 45.454722,
                "longitude": 9.181944,
            },
            {
                "name": "Gallerie d'Italia",
                "address": "Piazza della Scala 6",
                "latitude": 45.467500,
                "longitude": 9.189722,
            },
            {
                "name": "San Maurizio al Monastero Maggiore",
                "address": "Corso Magenta 15",
                "latitude": 45.465833,
                "longitude": 9.178889,
            },
            {
                "name": "Torre Branca",
                "address": "Viale Luigi Camoens",
                "latitude": 45.473056,
                "longitude": 9.174167,
            },
            {
                "name": "Basilica di San Lorenzo",
                "address": "Corso di Porta Ticinese 35",
                "latitude": 45.458056,
                "longitude": 9.182222,
            },
            {
                "name": "Villa Necchi Campiglio",
                "address": "Via Mozart 14",
                "latitude": 45.469167,
                "longitude": 9.202222,
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
            {
                "name": "Trattoria Sostanza",
                "address": "Via del Porcellana 25r",
                "latitude": 43.772500,
                "longitude": 11.248889,
            },
            {
                "name": "Osteria dell'Enoteca",
                "address": "Via Romana 70r",
                "latitude": 43.762222,
                "longitude": 11.243889,
            },
            {
                "name": "Cibrèo Trattoria",
                "address": "Via dei Macci 122r",
                "latitude": 43.769722,
                "longitude": 11.266111,
            },
            {
                "name": "Il Latini",
                "address": "Via dei Palchetti 6r",
                "latitude": 43.771389,
                "longitude": 11.249722,
            },
            {
                "name": "Trattoria Cammillo",
                "address": "Borgo San Jacopo 57r",
                "latitude": 43.767778,
                "longitude": 11.250556,
            },
            {
                "name": "Gucci Osteria",
                "address": "Piazza della Signoria 10",
                "latitude": 43.769772,
                "longitude": 11.255179,
            },
            {
                "name": "Ora d'Aria",
                "address": "Via dei Georgofili 11r",
                "latitude": 43.768333,
                "longitude": 11.255556,
            },
            {
                "name": "Trattoria 4 Leoni",
                "address": "Via de' Vellutini 1r",
                "latitude": 43.767222,
                "longitude": 11.248611,
            },
            {
                "name": "Buca dell'Orafo",
                "address": "Via dei Girolami 28r",
                "latitude": 43.768056,
                "longitude": 11.254167,
            },
            {
                "name": "Osteria Santo Spirito",
                "address": "Piazza Santo Spirito 16r",
                "latitude": 43.766667,
                "longitude": 11.247778,
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
            {
                "name": "Piazzale Michelangelo",
                "address": "Piazzale Michelangelo",
                "latitude": 43.762936,
                "longitude": 11.264900,
            },
            {
                "name": "Battistero di San Giovanni",
                "address": "Piazza San Giovanni",
                "latitude": 43.773056,
                "longitude": 11.255000,
            },
            {
                "name": "Basilica di Santa Croce",
                "address": "Piazza di Santa Croce 16",
                "latitude": 43.768333,
                "longitude": 11.262222,
            },
            {
                "name": "Cappelle Medicee",
                "address": "Piazza di Madonna degli Aldobrandini 6",
                "latitude": 43.775000,
                "longitude": 11.253889,
            },
            {
                "name": "Museo del Bargello",
                "address": "Via del Proconsolo 4",
                "latitude": 43.770556,
                "longitude": 11.258333,
            },
            {
                "name": "Basilica di San Lorenzo",
                "address": "Piazza San Lorenzo",
                "latitude": 43.774722,
                "longitude": 11.253611,
            },
            {
                "name": "Palazzo Vecchio",
                "address": "Piazza della Signoria",
                "latitude": 43.769444,
                "longitude": 11.256111,
            },
            {
                "name": "Giardino Bardini",
                "address": "Costa San Giorgio 2",
                "latitude": 43.763889,
                "longitude": 11.258611,
            },
            {
                "name": "Basilica di Santa Maria Novella",
                "address": "Piazza di Santa Maria Novella 18",
                "latitude": 43.774444,
                "longitude": 11.249444,
            },
            {
                "name": "Mercato Centrale",
                "address": "Piazza del Mercato Centrale",
                "latitude": 43.776667,
                "longitude": 11.253333,
            },
            {
                "name": "Museo di San Marco",
                "address": "Piazza San Marco 3",
                "latitude": 43.777500,
                "longitude": 11.259722,
            },
            {
                "name": "Cappella Brancacci",
                "address": "Piazza del Carmine 14",
                "latitude": 43.767500,
                "longitude": 11.242778,
            },
            {
                "name": "Forte di Belvedere",
                "address": "Via di San Leonardo 1",
                "latitude": 43.761944,
                "longitude": 11.252500,
            },
            {
                "name": "Museo Galileo",
                "address": "Piazza dei Giudici 1",
                "latitude": 43.767778,
                "longitude": 11.256389,
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
            {
                "name": "Trattoria alla Madonna",
                "address": "Calle de la Madona 594",
                "latitude": 45.438333,
                "longitude": 12.334722,
            },
            {
                "name": "Osteria Anice Stellato",
                "address": "Fondamenta de la Sensa 3272",
                "latitude": 45.446111,
                "longitude": 12.328611,
            },
            {
                "name": "Al Covo",
                "address": "Campiello de la Pescaria 3968",
                "latitude": 45.434167,
                "longitude": 12.348611,
            },
            {
                "name": "Vini da Gigio",
                "address": "Fondamenta San Felice 3628a",
                "latitude": 45.442222,
                "longitude": 12.333889,
            },
            {
                "name": "Osteria da Fiore",
                "address": "Calle del Scaleter 2202",
                "latitude": 45.438056,
                "longitude": 12.330833,
            },
            {
                "name": "Trattoria alla Rivetta",
                "address": "Castello 4625",
                "latitude": 45.434444,
                "longitude": 12.341111,
            },
            {
                "name": "Bacaro da Lele",
                "address": "Campo dei Tolentini 183",
                "latitude": 45.436944,
                "longitude": 12.320556,
            },
            {
                "name": "Osteria Bancogiro",
                "address": "Campo San Giacometto 122",
                "latitude": 45.438056,
                "longitude": 12.335278,
            },
            {
                "name": "Cantina Do Spade",
                "address": "Calle de le Do Spade 860",
                "latitude": 45.438611,
                "longitude": 12.334444,
            },
            {
                "name": "Ai Mercanti",
                "address": "Corte Coppo 4346a",
                "latitude": 45.434722,
                "longitude": 12.334444,
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
            {
                "name": "Gallerie dell'Accademia",
                "address": "Campo della Carità 1050",
                "latitude": 45.431111,
                "longitude": 12.328333,
            },
            {
                "name": "Basilica di Santa Maria della Salute",
                "address": "Fondamenta Salute 1/b",
                "latitude": 45.430833,
                "longitude": 12.334722,
            },
            {
                "name": "Collezione Peggy Guggenheim",
                "address": "Dorsoduro 701-704",
                "latitude": 45.430556,
                "longitude": 12.331389,
            },
            {
                "name": "Scala Contarini del Bovolo",
                "address": "Corte Contarini del Bovolo 4303",
                "latitude": 45.434167,
                "longitude": 12.334167,
            },
            {
                "name": "Ca' Rezzonico",
                "address": "Dorsoduro 3136",
                "latitude": 45.433611,
                "longitude": 12.327500,
            },
            {
                "name": "Basilica dei Frari",
                "address": "San Polo 3072",
                "latitude": 45.436944,
                "longitude": 12.326667,
            },
            {
                "name": "Teatro La Fenice",
                "address": "Campo San Fantin 1965",
                "latitude": 45.433889,
                "longitude": 12.333889,
            },
            {
                "name": "Isola di Murano",
                "address": "Murano",
                "latitude": 45.458611,
                "longitude": 12.353611,
            },
            {
                "name": "Isola di Burano",
                "address": "Burano",
                "latitude": 45.485278,
                "longitude": 12.416667,
            },
            {
                "name": "Ca' d'Oro",
                "address": "Cannaregio 3932",
                "latitude": 45.440556,
                "longitude": 12.333611,
            },
            {
                "name": "Torre dell'Orologio",
                "address": "Piazza San Marco 147",
                "latitude": 45.434444,
                "longitude": 12.338611,
            },
            {
                "name": "Campanile di San Marco",
                "address": "Piazza San Marco",
                "latitude": 45.434000,
                "longitude": 12.339000,
            },
            {
                "name": "Scuola Grande di San Rocco",
                "address": "San Polo 3052",
                "latitude": 45.436389,
                "longitude": 12.326111,
            },
            {
                "name": "Arsenale di Venezia",
                "address": "Campo de la Tana 2169/F",
                "latitude": 45.434722,
                "longitude": 12.352222,
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
            {
                "name": "Trattoria da Nennella",
                "address": "Vico Lungo Teatro Nuovo 103",
                "latitude": 40.840833,
                "longitude": 14.246944,
            },
            {
                "name": "Antica Osteria Pisano",
                "address": "Piazzetta Crocelle ai Mannesi 1",
                "latitude": 40.849167,
                "longitude": 14.260833,
            },
            {
                "name": "Trattoria da Concettina ai Tre Santi",
                "address": "Via Arena della Sanità 7bis",
                "latitude": 40.856389,
                "longitude": 14.251944,
            },
            {
                "name": "Pizzeria Di Matteo",
                "address": "Via dei Tribunali 94",
                "latitude": 40.851389,
                "longitude": 14.257222,
            },
            {
                "name": "Starita a Materdei",
                "address": "Via Materdei 27/28",
                "latitude": 40.856944,
                "longitude": 14.245833,
            },
            {
                "name": "Pizzeria Gorizia 1916",
                "address": "Via Bernardo Cavallino 8",
                "latitude": 40.856667,
                "longitude": 14.243056,
            },
            {
                "name": "Ristorante Il Comandante",
                "address": "Via Cristoforo Colombo 45",
                "latitude": 40.840556,
                "longitude": 14.255833,
            },
            {
                "name": "Trattoria Castel dell'Ovo",
                "address": "Via Luculliana 28",
                "latitude": 40.828611,
                "longitude": 14.248056,
            },
            {
                "name": "Osteria della Mattonella",
                "address": "Via Giovanni Nicotera 13",
                "latitude": 40.837778,
                "longitude": 14.243889,
            },
            {
                "name": "Trattoria San Ferdinando",
                "address": "Via Nardones 117",
                "latitude": 40.838056,
                "longitude": 14.246944,
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
            {
                "name": "Certosa e Museo di San Martino",
                "address": "Largo San Martino 5",
                "latitude": 40.844722,
                "longitude": 14.241389,
            },
            {
                "name": "Cattedrale di San Gennaro",
                "address": "Via Duomo 147",
                "latitude": 40.852500,
                "longitude": 14.259722,
            },
            {
                "name": "Palazzo Reale di Napoli",
                "address": "Piazza del Plebiscito 1",
                "latitude": 40.836389,
                "longitude": 14.250556,
            },
            {
                "name": "Castel Nuovo",
                "address": "Via Vittorio Emanuele III",
                "latitude": 40.838333,
                "longitude": 14.252500,
            },
            {
                "name": "Complesso di Santa Chiara",
                "address": "Via Santa Chiara 49c",
                "latitude": 40.847778,
                "longitude": 14.252778,
            },
            {
                "name": "Galleria Umberto I",
                "address": "Via San Carlo 15",
                "latitude": 40.838333,
                "longitude": 14.249167,
            },
            {
                "name": "Catacombe di San Gennaro",
                "address": "Via Capodimonte 13",
                "latitude": 40.868056,
                "longitude": 14.245278,
            },
            {
                "name": "Museo di Capodimonte",
                "address": "Via Miano 2",
                "latitude": 40.867500,
                "longitude": 14.250278,
            },
            {
                "name": "Piazza del Plebiscito",
                "address": "Piazza del Plebiscito",
                "latitude": 40.835833,
                "longitude": 14.248611,
            },
            {
                "name": "Lungomare Caracciolo",
                "address": "Via Francesco Caracciolo",
                "latitude": 40.827778,
                "longitude": 14.229722,
            },
            {
                "name": "Spaccanapoli",
                "address": "Via Benedetto Croce",
                "latitude": 40.848333,
                "longitude": 14.254722,
            },
            {
                "name": "Villa Pignatelli",
                "address": "Riviera di Chiaia 200",
                "latitude": 40.833056,
                "longitude": 14.229167,
            },
            {
                "name": "Orto Botanico di Napoli",
                "address": "Via Foria 223",
                "latitude": 40.860556,
                "longitude": 14.258889,
            },
            {
                "name": "Chiesa del Gesù Nuovo",
                "address": "Piazza del Gesù Nuovo",
                "latitude": 40.847778,
                "longitude": 14.251111,
            },
        ],
    },
}

ITALIAN_CITIES = list(PLACES.keys())

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
    website = factory.Faker("url")
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
            lambda o: (
                random.choice(
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
        )
        destination_place = factory.LazyAttribute(
            lambda o: (
                random.choice(
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
    notes = ""
    type_specific_data = factory.LazyFunction(dict)


class ChecklistItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.ChecklistItem"

    trip = factory.SubFactory(TripFactory)
    text = factory.Faker("sentence", nb_words=4)
    completed = False


class FamilyUnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.FamilyUnit"

    trip = factory.SubFactory(TripFactory)
    name = factory.Faker("last_name")
    shared_wallet = True


class ExpenseParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.ExpenseParticipant"

    trip = factory.SubFactory(TripFactory)
    name_snapshot = factory.Faker("first_name")
    is_child = False
    is_active = True


class ExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.Expense"

    trip = factory.SubFactory(TripFactory)
    title = factory.Faker("sentence", nb_words=3)
    amount = Decimal("30.00")
    date = factory.LazyAttribute(lambda o: o.trip.start_date)
    payer = factory.SubFactory(
        ExpenseParticipantFactory, trip=factory.SelfAttribute("..trip")
    )


class ExpenseShareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.ExpenseShare"

    expense = factory.SubFactory(ExpenseFactory)
    participant = factory.SubFactory(
        ExpenseParticipantFactory, trip=factory.SelfAttribute("..expense.trip")
    )


class StayBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "trips.StayBooking"

    trip = factory.SubFactory(TripFactory)
    destination = factory.LazyAttribute(lambda o: o.trip.destination)
    created_by = factory.LazyAttribute(lambda o: o.trip.author)
    provider = "smart"
    includes_author = True
