---
# cache
title: Cache Google Places API
status: scrapped
type: task
priority: "2"
created_at: 2026-03-31T06:02:32Z
updated_at: 2026-04-04T05:44:25Z
---

# Cache Google Places API

## Objective
Reduce Google Places API calls by 80%+ with caching.

## Required changes

### 1. `trips/views.py` - enrich_stay() (line ~1858)
```python
from django.core.cache import cache

def enrich_stay(request, stay_id):
    """Enrich a stay's details using Google Places API."""
    stay = get_object_or_404(Stay, pk=stay_id, author=request.user)

    if not stay.address:
        return TemplateResponse(request, "trips/stay-enrich-preview.html", {
            "error_message": _("Stay has no address.")
        })

    api_key = settings.GOOGLE_PLACES_API_KEY
    if not api_key:
        return TemplateResponse(request, "trips/stay-enrich-preview.html", {
            "error_message": _("Google Places API key is not configured.")
        })

    # Generate cache key from address
    cache_key = f"google_places_{hashlib.md5(stay.address.encode(), usedforsecurity=False).hexdigest()}"

    # Try cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Google Places cache hit for: {stay.address}")
        place_data = cached_data
    else:
        # Search API call
        search_url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,"
                               "places.location,places.phoneNumber,places.website,"
                               "places.openingHours,places.googleMapsUri"
        }
        body = {"textQuery": stay.address}

        try:
            response = httpx.post(search_url, headers=headers, json=body, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if not data.get("places"):
                return TemplateResponse(request, "trips/stay-enrich-preview.html", {
                    "error_message": _("No place found for this address.")
                })

            place = data["places"][0]
            place_id = place["id"]

            # Details API call
            details_url = f"https://places.googleapis.com/v1/places/{place_id}"
            details_response = httpx.get(details_url, headers=headers, timeout=10.0)
            details_response.raise_for_status()
            place_data = details_response.json()

            # Cache for 24 hours
            cache.set(cache_key, place_data, 86400)
            logger.info(f"Google Places cached for: {stay.address}")

        except httpx.TimeoutException:
            return TemplateResponse(request, "trips/stay-enrich-preview.html", {
                "error_message": _("Google Places API request timed out.")
            })
        except Exception as e:
            logger.error(f"Error calling Google Places API: {e}")
            return TemplateResponse(request, "trips/stay-enrich-preview.html", {
                "error_message": _("Error fetching place details.")
            })

    # ... rest of code uses place_data
```

### 2. `trips/views.py` - enrich_event() (line ~2032)
Apply the same caching logic used for `enrich_stay()`.

```python
# Cache key based on address
cache_key = f"google_places_{hashlib.md5(event.address.encode(), usedforsecurity=False).hexdigest()}"

# Try cache
cached_data = cache.get(cache_key)
if cached_data:
    place_data = cached_data
else:
    # ... API calls ...
    cache.set(cache_key, place_data, 86400)
```

## Test
1. Enrich a stay → first time calls API
2. Enrich same stay → uses cache
3. Verify log for "cache hit"
4. Run `just ftest`

## Acceptance criteria
- [ ] Cache hit for already enriched addresses
- [ ] Timeout handled correctly
- [ ] All tests pass
- [ ] Log shows cache hit/miss
