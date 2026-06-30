import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Isolate tests: the locmem cache persists across tests in-process."""
    cache.clear()
    yield
    cache.clear()
