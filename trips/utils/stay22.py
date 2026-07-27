from urllib.parse import urlencode

STAY22_ROAM_URL = "https://www.stay22.com/allez/roam"
# Backwards-compatible alias.
STAY22_BASE_URL = STAY22_ROAM_URL


def build_stay22_url(
    *, aid, address, checkin, checkout, adults, children=0, provider="smart"
):
    """Build a monetized Stay22 Allez roam URL with pre-filled search params.

    ``checkin``/``checkout`` are ``date`` objects, formatted as ``YYYY-MM-DD``.
    ``children`` is appended only when greater than zero.

    ``provider="smart"`` lets roam pick the best OTA. A specific provider
    (``booking``/``expedia``) is forced via the documented ``provider`` query
    param, which overrides roam's AI selection while keeping the traffic
    monetized through the same Allez endpoint.
    """
    params = {
        "aid": aid,
        "address": address,
        "checkin": checkin.strftime("%Y-%m-%d"),
        "checkout": checkout.strftime("%Y-%m-%d"),
        "adults": adults,
    }
    if children:
        params["children"] = children
    if provider and provider != "smart":
        params["provider"] = provider
    return f"{STAY22_ROAM_URL}?{urlencode(params)}"
