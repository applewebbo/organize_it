import hashlib
import logging
import re
from io import BytesIO

import requests
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

logger = logging.getLogger(__name__)

WIKIMEDIA_USER_AGENT = "OrganizeIt/1.0 (https://github.com/applewebbo/organize_it)"

# Wikimedia Commons has no orientation filter like Unsplash, so aspect ratio
# is checked client-side to exclude panoramas and portrait/odd crops.
WIKIMEDIA_MIN_ASPECT_RATIO = 1.05
WIKIMEDIA_MAX_ASPECT_RATIO = 2.2
# Over-fetch since many results get filtered out by aspect ratio.
WIKIMEDIA_OVERFETCH_FACTOR = 3


def search_unsplash_photos(query, per_page=5, orientation="landscape"):
    """
    Search Unsplash for photos with caching.

    Args:
        query: Search query (typically trip destination)
        per_page: Number of results (default 5 for UI)
        orientation: Photo orientation (default 'landscape')

    Returns:
        List of photo dicts or None on error
    """
    from django.conf import settings

    # Generate cache key
    cache_data = f"unsplash_{query}_{per_page}_{orientation}"
    cache_key = hashlib.md5(cache_data.encode(), usedforsecurity=False).hexdigest()

    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Unsplash cache hit for query: {query}")
        return cached_result

    # Check API key
    api_key = settings.UNSPLASH_ACCESS_KEY
    if not api_key:
        logger.error("Unsplash API key not configured")
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
            photos.append(
                {
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
                    "source": "unsplash",
                }
            )

        # Cache for 6 hours (21600 seconds)
        cache.set(cache_key, photos, 21600)
        logger.info(f"Unsplash search successful: {len(photos)} results for '{query}'")
        return photos

    except requests.exceptions.Timeout:
        logger.error("Unsplash API timeout")
    except requests.RequestException as e:
        logger.error(f"Unsplash API error: {e}")

    return None


def download_unsplash_photo(photo_data):
    """
    Download photo from Unsplash and return file content.
    Also triggers Unsplash download tracking (TOS requirement).

    Args:
        photo_data: Photo dict from search_unsplash_photos

    Returns:
        Tuple of (image_content, metadata_dict) or (None, None)
    """
    from django.conf import settings

    api_key = settings.UNSPLASH_ACCESS_KEY
    if not api_key:
        return None, None

    try:
        # 1. Trigger download tracking (Unsplash TOS requirement)
        download_location = photo_data["links"]["download_location"]
        requests.get(
            download_location,
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=5,
        )

        # 2. Download the actual image
        image_url = photo_data["urls"]["regular"]
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # 3. Prepare metadata
        metadata = {
            "source": "unsplash",
            "unsplash_id": photo_data["id"],
            "photographer": photo_data["user"]["name"],
            "photographer_url": photo_data["user"]["profile"],
            "photo_url": photo_data["links"]["html"],
            "download_location": download_location,
        }

        logger.info(f"Downloaded Unsplash photo: {photo_data['id']}")
        return response.content, metadata

    except requests.RequestException as e:
        logger.error(f"Failed to download Unsplash photo: {e}")
        return None, None


def search_wikimedia_photos(query, per_page=5):
    """
    Search Wikimedia Commons for photos with caching.

    Used as a fallback source alongside Unsplash: Commons has much broader
    coverage of lesser-known destinations since it mirrors Wikipedia's
    geo-tagged photos, and requires no API key.

    Args:
        query: Search query (typically trip destination)
        per_page: Number of results (default 5 for UI)

    Returns:
        List of photo dicts or None on error
    """
    cache_data = f"wikimedia_{query}_{per_page}"
    cache_key = hashlib.md5(cache_data.encode(), usedforsecurity=False).hexdigest()

    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Wikimedia cache hit for query: {query}")
        return cached_result

    try:
        response = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"{query} filetype:bitmap",
                "gsrnamespace": 6,
                "gsrlimit": per_page * WIKIMEDIA_OVERFETCH_FACTOR,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime|size",
                "iiurlwidth": 400,
            },
            headers={"User-Agent": WIKIMEDIA_USER_AGENT},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        photos = []
        for page_id, page in pages.items():
            if len(photos) >= per_page:
                break

            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue
            info = imageinfo[0]
            if not info.get("mime", "").startswith("image/"):
                continue

            width, height = info.get("width"), info.get("height")
            if not width or not height:
                continue
            aspect_ratio = width / height
            if not (
                WIKIMEDIA_MIN_ASPECT_RATIO <= aspect_ratio <= WIKIMEDIA_MAX_ASPECT_RATIO
            ):
                continue

            extmetadata = info.get("extmetadata", {})
            artist = re.sub(
                r"<[^>]+>", "", extmetadata.get("Artist", {}).get("value", "")
            ).strip()
            title = re.sub(r"^File:", "", page.get("title", "")).rsplit(".", 1)[0]

            photos.append(
                {
                    "id": f"wikimedia_{page_id}",
                    "urls": {
                        "small": info.get("thumburl", info["url"]),
                        "regular": info["url"],
                    },
                    "user": {
                        "name": artist or "Wikimedia Commons",
                        "profile": info.get("descriptionurl", info["url"]),
                    },
                    "alt_description": title,
                    "source": "wikimedia",
                }
            )

        cache.set(cache_key, photos, 21600)
        logger.info(f"Wikimedia search successful: {len(photos)} results for '{query}'")
        return photos

    except requests.exceptions.Timeout:
        logger.error("Wikimedia API timeout")
    except requests.RequestException as e:
        logger.error(f"Wikimedia API error: {e}")

    return None


def download_wikimedia_photo(photo_data):
    """
    Download photo from Wikimedia Commons and return file content.

    Args:
        photo_data: Photo dict from search_wikimedia_photos

    Returns:
        Tuple of (image_content, metadata_dict) or (None, None)
    """
    try:
        image_url = photo_data["urls"]["regular"]
        response = requests.get(
            image_url,
            headers={"User-Agent": WIKIMEDIA_USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()

        metadata = {
            "source": "wikimedia",
            "wikimedia_id": photo_data["id"],
            "photographer": photo_data["user"]["name"],
            "photographer_url": photo_data["user"]["profile"],
            "photo_url": photo_data["user"]["profile"],
        }

        logger.info(f"Downloaded Wikimedia photo: {photo_data['id']}")
        return response.content, metadata

    except requests.RequestException as e:
        logger.error(f"Failed to download Wikimedia photo: {e}")
        return None, None


def process_trip_image(image_file, max_size_mb=2):
    """
    Process uploaded image: validate size, resize if needed, ensure landscape.

    Args:
        image_file: UploadedFile or bytes
        max_size_mb: Maximum file size in MB

    Returns:
        Processed InMemoryUploadedFile or None if invalid
    """
    try:
        # Handle bytes vs UploadedFile
        if isinstance(image_file, bytes):
            img = Image.open(BytesIO(image_file))
            original_name = "unsplash_photo.jpg"
        else:
            img = Image.open(image_file)
            original_name = image_file.name

            # Check file size
            image_file.seek(0, 2)  # Seek to end
            size_mb = image_file.size / (1024 * 1024)
            image_file.seek(0)  # Reset

            if size_mb > max_size_mb:
                logger.warning(f"Image too large: {size_mb:.2f}MB > {max_size_mb}MB")
                # Continue to resize instead of rejecting

        # Convert to RGB if needed (handle RGBA, grayscale, etc)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Ensure landscape orientation (width > height)
        width, height = img.size
        if height > width:
            # Rotate to landscape
            img = img.rotate(90, expand=True)
            width, height = img.size

        # Calculate target dimensions maintaining aspect ratio
        # Target max dimensions: 1200x800 for landscape
        target_width = 1200
        target_height = 800
        aspect_ratio = width / height

        if aspect_ratio > (target_width / target_height):
            # Image is wider than target
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            # Image is taller than target
            new_height = target_height
            new_width = int(target_height * aspect_ratio)

        # Resize if larger than target
        if width > new_width or height > new_height:
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(
                f"Resized image from {width}x{height} to {new_width}x{new_height}"
            )

        # Save to BytesIO
        output = BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        output.seek(0)

        # Create InMemoryUploadedFile
        processed_file = InMemoryUploadedFile(
            output,
            "ImageField",
            original_name,
            "image/jpeg",
            output.getbuffer().nbytes,
            None,
        )

        return processed_file

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return None
