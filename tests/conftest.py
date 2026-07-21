"""Project-wide test fixtures."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_mapbox_geocoding():
    """Stub Mapbox geocoding for the whole suite so tests never hit the network.

    Every source module calls ``geocoder.mapbox(...)``; patching it at the
    library source gives all callers (trips, accounts, management commands)
    deterministic coordinates offline. Without this, trip/event/stay creation
    made real Mapbox calls that flaked under parallel runs (see #392).

    Tests that assert on specific geocoding behaviour patch ``geocoder.mapbox``
    locally, which overrides this default within their own scope.
    """

    def fake_mapbox(location=None, *args, **kwargs):
        # Mirror Mapbox: a blank query yields no result (latlng None), a real
        # one resolves to fixed coordinates.
        has_query = bool(location and str(location).strip())
        result = MagicMock(ok=has_query)
        result.latlng = [41.9, 12.5] if has_query else None
        return result

    with patch("geocoder.mapbox", side_effect=fake_mapbox) as mock_mapbox:
        yield mock_mapbox
