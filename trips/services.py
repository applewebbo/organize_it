import logging
from dataclasses import dataclass, field

import requests
from django.conf import settings

from trips.utils import convert_google_opening_hours

logger = logging.getLogger(__name__)

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# Fields returned for search results (minimal, cost-efficient)
SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location"
)

# Fields returned for place details
DETAILS_FIELD_MASK = "websiteUri,internationalPhoneNumber,regularOpeningHours"


class GooglePlacesError(Exception):
    pass


@dataclass
class PlaceResult:
    place_id: str
    name: str
    address: str
    lat: float
    lng: float


@dataclass
class PlaceDetails:
    place_id: str
    website: str = ""
    phone_number: str = ""
    opening_hours: dict | None = field(default=None)


class GooglePlacesClient:
    """
    Server-side proxy for Google Places API (New).
    The API key never leaves the server.
    """

    def __init__(self):
        self.timeout = 5

    @property
    def api_key(self) -> str:
        return settings.GOOGLE_PLACES_API_KEY

    def _headers(self, field_mask: str) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

    def search_text(self, query: str, max_results: int = 10) -> list[PlaceResult]:
        """
        Search places by free-text query.
        Returns a list of PlaceResult with minimal fields.
        Raises GooglePlacesError on failure.
        """
        if not self.api_key:
            raise GooglePlacesError("Google Places API key is not configured.")

        payload = {"textQuery": query, "maxResultCount": max_results}
        try:
            response = requests.post(
                PLACES_SEARCH_URL,
                json=payload,
                headers=self._headers(SEARCH_FIELD_MASK),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            raise GooglePlacesError("Google Places API request timed out.") from e
        except requests.RequestException as e:
            detail = e.response.text if e.response is not None else str(e)
            logger.error("Google Places searchText error: %s", detail)
            raise GooglePlacesError(f"API error: {detail}") from e

        data = response.json()
        results = []
        for place in data.get("places", []):
            loc = place.get("location", {})
            results.append(
                PlaceResult(
                    place_id=place["id"],
                    name=place.get("displayName", {}).get("text", ""),
                    address=place.get("formattedAddress", ""),
                    lat=loc.get("latitude", 0.0),
                    lng=loc.get("longitude", 0.0),
                )
            )
        return results

    def get_place_details(self, place_id: str) -> PlaceDetails:
        """
        Fetch details for a known place_id: website, phone, opening hours.
        Raises GooglePlacesError on failure.
        """
        if not self.api_key:
            raise GooglePlacesError("Google Places API key is not configured.")

        url = PLACES_DETAILS_URL.format(place_id=place_id)
        try:
            response = requests.get(
                url,
                headers=self._headers(DETAILS_FIELD_MASK),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise GooglePlacesError("Google Places API request timed out.") from exc
        except requests.RequestException as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            logger.error("Google Places details error for %s: %s", place_id, detail)
            raise GooglePlacesError(f"API error: {detail}") from exc

        data = response.json()
        return PlaceDetails(
            place_id=place_id,
            website=data.get("websiteUri", ""),
            phone_number=data.get("internationalPhoneNumber", ""),
            opening_hours=convert_google_opening_hours(data.get("regularOpeningHours")),
        )

    def search_place_id(self, query: str) -> str | None:
        """
        Convenience method: search by query and return the first place_id only.
        Used by enrich_stay / enrich_event views.
        """
        if not self.api_key:
            raise GooglePlacesError("Google Places API key is not configured.")

        payload = {"textQuery": query}
        try:
            response = requests.post(
                PLACES_SEARCH_URL,
                json=payload,
                headers=self._headers("places.id"),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise GooglePlacesError("Google Places API request timed out.") from exc
        except requests.RequestException as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise GooglePlacesError(f"API error: {detail}") from exc

        places = response.json().get("places", [])
        return places[0]["id"] if places else None
