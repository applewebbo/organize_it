from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Isolate tests: the locmem cache persists across tests in-process."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def deterministic_trip_geocoding():
    """Pin trip destination geocoding to Rome so grounded-place distance checks
    are deterministic (offline) instead of hitting Mapbox with a random city."""
    with patch("trips.models.geocoder.mapbox") as mock_mapbox:
        mock_mapbox.return_value = MagicMock(latlng=[41.9, 12.5])
        yield
