"""Weather forecast utilities using Open-Meteo API (open-meteo.com)."""

import logging
from datetime import date

import httpx
from django.utils import timezone

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16

# WMO weather interpretation codes mapped to Phosphor icon class and label
WMO_CODE_MAP = {
    0: {"icon": "ph-sun", "label": "Clear sky"},
    1: {"icon": "ph-sun", "label": "Mainly clear"},
    2: {"icon": "ph-cloud-sun", "label": "Partly cloudy"},
    3: {"icon": "ph-cloud", "label": "Overcast"},
    45: {"icon": "ph-cloud-fog", "label": "Fog"},
    48: {"icon": "ph-cloud-fog", "label": "Icy fog"},
    51: {"icon": "ph-cloud-drizzle", "label": "Light drizzle"},
    53: {"icon": "ph-cloud-drizzle", "label": "Moderate drizzle"},
    55: {"icon": "ph-cloud-drizzle", "label": "Dense drizzle"},
    56: {"icon": "ph-cloud-drizzle", "label": "Freezing drizzle"},
    57: {"icon": "ph-cloud-drizzle", "label": "Heavy freezing drizzle"},
    61: {"icon": "ph-cloud-rain", "label": "Slight rain"},
    63: {"icon": "ph-cloud-rain", "label": "Moderate rain"},
    65: {"icon": "ph-cloud-rain", "label": "Heavy rain"},
    66: {"icon": "ph-cloud-rain", "label": "Freezing rain"},
    67: {"icon": "ph-cloud-rain", "label": "Heavy freezing rain"},
    71: {"icon": "ph-snowflake", "label": "Slight snow"},
    73: {"icon": "ph-snowflake", "label": "Moderate snow"},
    75: {"icon": "ph-snowflake", "label": "Heavy snow"},
    77: {"icon": "ph-snowflake", "label": "Snow grains"},
    80: {"icon": "ph-cloud-rain", "label": "Slight showers"},
    81: {"icon": "ph-cloud-rain", "label": "Moderate showers"},
    82: {"icon": "ph-cloud-rain", "label": "Heavy showers"},
    85: {"icon": "ph-snowflake", "label": "Slight snow showers"},
    86: {"icon": "ph-snowflake", "label": "Heavy snow showers"},
    95: {"icon": "ph-cloud-lightning", "label": "Thunderstorm"},
    96: {"icon": "ph-cloud-lightning", "label": "Thunderstorm with hail"},
    99: {"icon": "ph-cloud-lightning", "label": "Thunderstorm with heavy hail"},
}


def get_wmo_info(code):
    """Return icon and label for a WMO weather code, with fallback."""
    return WMO_CODE_MAP.get(code, {"icon": "ph-cloud", "label": "Unknown"})


def parse_weather_response(data, target_date):
    """
    Parse an Open-Meteo daily forecast response and extract data for a specific date.

    Returns a dict with weather data or None if the date is not in the response.
    """
    daily = data.get("daily", {})
    times = daily.get("time", [])
    target_str = (
        target_date.isoformat() if isinstance(target_date, date) else target_date
    )

    if target_str not in times:
        return None

    idx = times.index(target_str)

    weather_code = daily.get("weather_code", [])[idx]
    wmo = get_wmo_info(weather_code)

    return {
        "temperature_max": daily.get("temperature_2m_max", [])[idx],
        "temperature_min": daily.get("temperature_2m_min", [])[idx],
        "precipitation_sum": daily.get("precipitation_sum", [])[idx],
        "wind_speed_max": daily.get("wind_speed_10m_max", [])[idx],
        "weather_code": weather_code,
        "weather_icon": wmo["icon"],
        "weather_label": wmo["label"],
    }


def get_coordinates_for_day(day):
    """
    Resolve lat/lng coordinates for a day.

    Priority:
    1. First event of the day with coordinates
    2. Stay of the day with coordinates
    3. None (weather unavailable)
    """
    for event in day.events.all():
        if event.latitude is not None and event.longitude is not None:
            return event.latitude, event.longitude

    if day.stay and day.stay.latitude is not None and day.stay.longitude is not None:
        return day.stay.latitude, day.stay.longitude

    return None


def fetch_raw_weather(latitude, longitude, forecast_days=FORECAST_DAYS):
    """
    Fetch raw weather forecast from Open-Meteo API.

    Returns the parsed JSON response or raises an exception on failure.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }
    response = httpx.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_weather_for_day(day):
    """
    Fetch and cache weather data for a single day.

    Uses coordinates from the day's first event or stay.
    Saves weather_data and weather_fetched_at on the day instance.
    """
    coords = get_coordinates_for_day(day)
    if coords is None:
        logger.debug("No coordinates for day %s, skipping weather fetch", day)
        return

    lat, lon = coords
    try:
        raw = fetch_raw_weather(lat, lon)
    except Exception as exc:
        logger.warning("Weather fetch failed for day %s: %s", day, exc)
        return

    weather = parse_weather_response(raw, day.date)
    if weather is None:
        logger.debug("Date %s not in Open-Meteo response for day %s", day.date, day)
        return

    day.weather_data = weather
    day.weather_fetched_at = timezone.now()
    day.save(update_fields=["weather_data", "weather_fetched_at"])


def fetch_weather_for_trip(trip):
    """Fetch and cache weather for all days of a trip."""
    for day in trip.days.all():
        fetch_weather_for_day(day)
