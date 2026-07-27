from datetime import date
from urllib.parse import parse_qs, urlparse

from trips.utils.stay22 import STAY22_BASE_URL, STAY22_ROAM_URL, build_stay22_url


class TestBuildStay22Url:
    def test_base_url_and_required_params(self):
        url = build_stay22_url(
            aid="test123",
            address="Via Roma 1, Milano",
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 5),
            adults=2,
        )
        parsed = urlparse(url)
        assert url.startswith(STAY22_ROAM_URL)
        params = parse_qs(parsed.query)
        assert params["aid"] == ["test123"]
        assert params["address"] == ["Via Roma 1, Milano"]
        assert params["checkin"] == ["2026-08-01"]
        assert params["checkout"] == ["2026-08-05"]
        assert params["adults"] == ["2"]

    def test_base_url_alias_matches_roam(self):
        assert STAY22_BASE_URL == STAY22_ROAM_URL

    def test_children_included_only_when_present(self):
        url = build_stay22_url(
            aid="a",
            address="x",
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 2),
            adults=2,
            children=3,
        )
        assert "children=3" in url

    def test_children_omitted_when_zero(self):
        url = build_stay22_url(
            aid="a",
            address="x",
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 2),
            adults=2,
            children=0,
        )
        assert "children" not in url

    def test_smart_provider_not_in_url(self):
        url = build_stay22_url(
            aid="a",
            address="x",
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 2),
            adults=1,
            provider="smart",
        )
        assert "provider" not in url

    def test_booking_provider_forced_on_roam(self):
        url = build_stay22_url(
            aid="a",
            address="x",
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 2),
            adults=1,
            provider="booking",
        )
        assert url.startswith(STAY22_ROAM_URL)
        assert "provider=booking" in url

    def test_expedia_provider_forced_on_roam(self):
        url = build_stay22_url(
            aid="a",
            address="x",
            checkin=date(2026, 8, 1),
            checkout=date(2026, 8, 2),
            adults=1,
            provider="expedia",
        )
        assert url.startswith(STAY22_ROAM_URL)
        assert "provider=expedia" in url
