---
# optimize
title: Optimize Unsplash API caching
status: scrapped
type: task
priority: "3"
created_at: 2026-03-31T06:02:32Z
updated_at: 2026-04-04T05:44:25Z
---

# Optimize Unsplash API caching

## Objective
Reduce Unsplash API calls by 90%+ with extended caching.

## Required changes

### 1. `trips/utils.py` - search_unsplash_photos() (line ~293)
```python
def search_unsplash_photos(query, per_page=3, orientation="landscape"):
    """
    Search Unsplash for photos with caching.
    """
    from django.conf import settings

    # Generate cache key
    cache_data = f"unsplash_{query}_{per_page}_{orientation}"
    cache_key = hashlib.md5(cache_data.encode(), usedforsecurity=False).hexdigest()

    # Check cache - extended to 24 hours
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Unsplash cache hit for query: {query}")
        return cached_result

    # Check API key
    api_key = settings.UNSPLASH_ACCESS_KEY
    if not api_key:
        logger.error("Unsplash API key not configured")
        return None

    # Rate limiting check
    rate_limit_key = f"unsplash_rate_limit_{int(time.time() / 60)}"  # Per minute
    rate_limit = cache.get(rate_limit_key, 0)
    if rate_limit > 50:  # Unsplash limit: 50/hour for free tier
        logger.warning(f"Unsplash rate limit exceeded: {rate_limit} requests/minute")
        return None

    # API request
    try:
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": per_page, "orientation": orientation},
            headers={"Authorization": f"Client-ID {api_key}", "Accept-Version": "v1"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        # Extract relevant fields
        photos = []
        for result in data.get("results", []):
            photos.append({
                "id": result["id"],
                "urls": {
                    "regular": result["urls"]["regular"],
                    "small": result["urls"]["small"],
                    "thumb": result["urls"]["thumb"],
                },
                "user": {
                    "name": result["user"]["name"],
                    "username": result["user"]["username"],
                    "profile": result["user"]["links"]["html"],
                },
                "links": {
                    "html": result["links"]["html"],
                    "download_location": result["links"]["download_location"],
                },
                "alt_description": result.get("alt_description", ""),
            })

        # Cache for 24 hours (86400 seconds) - EXTENDED
        cache.set(cache_key, photos, 86400)

        # Update rate limit counter
        cache.set(rate_limit_key, rate_limit + 1, 60)

        logger.info(f"Unsplash search successful: {len(photos)} results for '{query}'")
        return photos

    except requests.exceptions.Timeout:
        logger.error("Unsplash API timeout")
    except requests.RequestException as e:
        logger.error(f"Unsplash API error: {e}")

    return None
```

### 2. `trips/utils.py` - download_unsplash_photo() (line ~371)
```python
def download_unsplash_photo(photo_data):
    """
    Download photo from Unsplash and return file content.
    Also triggers Unsplash download tracking (TOS requirement).
    """
    from django.conf import settings

    api_key = settings.UNSPLASH_ACCESS_KEY
    if not api_key:
        return None, None

    # Cache download URL to avoid duplicate tracking calls
    download_cache_key = f"unsplash_downloaded_{photo_data['id']}"
    if cache.get(download_cache_key):
        logger.info(f"Unsplash photo already downloaded: {photo_data['id']}")
        # Return cached image if available
        cached_image = cache.get(f"unsplash_image_{photo_data['id']}")
        if cached_image:
            return cached_image, cache.get(f"unsplash_metadata_{photo_data['id']}")

    try:
        # 1. Trigger download tracking (Unsplash TOS requirement)
        download_location = photo_data["links"]["download_location"]
        tracking_response = requests.get(
            download_location,
            headers={"Authorization": f"Client-ID {api_key}", "Accept-Version": "v1"},
            timeout=5,
        )
        tracking_response.raise_for_status()

        # 2. Download actual image
        image_url = photo_data["urls"]["regular"]
        image_response = requests.get(image_url, timeout=10)
        image_response.raise_for_status()

        # Cache image and metadata
        image_content = image_response.content
        metadata = {
            "source": "unsplash",
            "unsplash_id": photo_data["id"],
            "photographer": photo_data["user"]["name"],
            "photographer_url": photo_data["user"]["profile"],
            "download_location": download_location,
        }

        # Cache for 1 hour (images are large)
        cache.set(download_cache_key, True, 3600)
        cache.set(f"unsplash_image_{photo_data['id']}", image_content, 3600)
        cache.set(f"unsplash_metadata_{photo_data['id']}", metadata, 3600)

        logger.info(f"Downloaded Unsplash photo: {photo_data['id']}")
        return image_content, metadata

    except requests.RequestException as e:
        logger.error(f"Failed to download Unsplash photo: {e}")

    return None, None
```

## Test
1. Search images for same destination → cache hit
2. Download same image → no duplicate tracking
3. Verify log for cache hit
4. Run `just ftest`

## Acceptance criteria
- [ ] Cache extended to 24 hours for search
- [ ] Download tracking called once per image
- [ ] Rate limiting active
- [ ] All tests pass
