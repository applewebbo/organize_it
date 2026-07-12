import csv
from pathlib import Path

from django.conf import settings

from trips.models import MainTransfer

# Cache for CSV data (lazy loading)
_AIRPORTS_CACHE = None
_STATIONS_CACHE = None


def get_flight_origin_icao(transfer):
    """Return ICAO code for origin airport of a flight transfer, or empty string."""
    if transfer and transfer.type == MainTransfer.Type.PLANE and transfer.origin_code:
        airport = get_airport_by_iata(transfer.origin_code)
        return airport.get("icao_code", "") if airport else ""
    return ""


def load_airports():
    """
    Load airports from CSV (with cache).
    Returns list of airport dicts with: iata_code, icao_code, name, city, latitude, longitude
    """
    global _AIRPORTS_CACHE

    if _AIRPORTS_CACHE is not None:
        return _AIRPORTS_CACHE

    airports = []
    csv_path = Path(settings.BASE_DIR) / "trips" / "data" / "airports_simple.csv"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            airports.append(
                {
                    "iata_code": row["iata_code"],
                    "icao_code": row.get("icao_code", ""),
                    "name": row["name"],
                    "city": row["city"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )

    _AIRPORTS_CACHE = airports
    return airports


def load_train_stations():
    """
    Load train stations from CSV (with cache).
    Returns list of station dicts with: id, name, country, latitude, longitude
    """
    global _STATIONS_CACHE

    if _STATIONS_CACHE is not None:
        return _STATIONS_CACHE

    stations = []
    csv_path = Path(settings.BASE_DIR) / "trips" / "data" / "stations_simplified.csv"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip stations without coordinates
            if not row.get("latitude") or not row.get("longitude"):
                continue

            try:
                stations.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "country": row["country"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                    }
                )
            except ValueError, KeyError:
                # Skip rows with invalid data
                continue

    _STATIONS_CACHE = stations
    return stations


def search_airports(query, limit=10):
    """
    Search airports by name, city, or IATA code.

    Args:
        query: Search text
        limit: Maximum number of results

    Returns:
        List of airports matching the query
    """
    airports = load_airports()
    query_lower = query.lower()

    results = []
    for airport in airports:
        if (
            query_lower in airport["iata_code"].lower()
            or query_lower in airport["name"].lower()
            or query_lower in airport["city"].lower()
        ):
            results.append(airport)
            if len(results) >= limit:
                break

    return results


def search_train_stations(query, limit=10):
    """
    Search train stations by name or country.

    Args:
        query: Search text
        limit: Maximum number of results

    Returns:
        List of stations matching the query
    """
    stations = load_train_stations()
    query_lower = query.lower()

    results = []
    for station in stations:
        if (
            query_lower in station["name"].lower()
            or query_lower in station["country"].lower()
        ):
            results.append(station)
            if len(results) >= limit:
                break

    return results


def get_airport_by_iata(iata_code):
    """
    Find airport by IATA code.

    Args:
        iata_code: IATA code (e.g., 'FCO')

    Returns:
        Airport dict or None if not found
    """
    airports = load_airports()
    for airport in airports:
        if airport["iata_code"].upper() == iata_code.upper():
            return airport
    return None


def get_station_by_id(station_id):
    """
    Find train station by ID.

    Args:
        station_id: Station ID as string

    Returns:
        Station dict or None if not found
    """
    stations = load_train_stations()
    for station in stations:
        if station["id"] == str(station_id):
            return station
    return None
