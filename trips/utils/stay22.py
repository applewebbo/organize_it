from urllib.parse import urlencode

STAY22_BASE_URL = "https://www.stay22.com/allez/roam"


def build_stay22_url(
    *, aid, address, checkin, checkout, adults, children=0, provider="smart"
):
    """Build a Stay22 Allez smart-link URL with pre-filled search parameters.

    ``checkin``/``checkout`` are ``date`` objects, formatted as ``YYYY-MM-DD``.
    ``children`` is appended only when greater than zero. A non-``smart``
    ``provider`` forces the destination platform via the native override.
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
    return f"{STAY22_BASE_URL}?{urlencode(params)}"
