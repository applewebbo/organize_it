import pytest

from trips.models import Stay

pytestmark = pytest.mark.django_db


def test_stay_google_maps_directions_url_with_address_and_city():
    stay = Stay(address="Via Roma 1", city="Roma")
    assert (
        stay.google_maps_directions_url
        == "https://www.google.com/maps/dir/?api=1&destination=Via%20Roma%201%2C%20Roma"
    )


def test_stay_google_maps_directions_url_with_only_address():
    stay = Stay(address="Via Roma 1", city="")
    assert (
        stay.google_maps_directions_url
        == "https://www.google.com/maps/dir/?api=1&destination=Via%20Roma%201"
    )


def test_stay_google_maps_directions_url_with_only_city():
    stay = Stay(address="", city="Roma")
    assert (
        stay.google_maps_directions_url
        == "https://www.google.com/maps/dir/?api=1&destination=%2C%20Roma"
    )


def test_stay_google_maps_directions_url_with_lat_lng_only():
    stay = Stay(address="", city="", latitude=41.9, longitude=12.5)
    assert (
        stay.google_maps_directions_url
        == "https://www.google.com/maps/dir/?api=1&destination=41.9,12.5"
    )


def test_stay_google_maps_directions_url_empty():
    stay = Stay(address="", city="", latitude=None, longitude=None)
    assert stay.google_maps_directions_url is None
