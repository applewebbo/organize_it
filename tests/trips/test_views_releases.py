import pytest
from pytest_django.asserts import assertTemplateUsed

from trips.releases import RELEASES
from trips.views.releases import RELEASES_PER_PAGE

pytestmark = pytest.mark.django_db


class TestReleasesPage:
    def test_page_renders(self, client):
        response = client.get("/novita/")

        assert response.status_code == 200
        assertTemplateUsed(response, "pages/releases.html")

    def test_an_anonymous_visitor_can_reach_it(self, client):
        response = client.get("/novita/")

        assert response.status_code == 200

    def test_first_page_carries_the_latest_releases(self, client):
        response = client.get("/novita/")

        page = response.context["releases"]
        assert list(page.object_list) == RELEASES[:RELEASES_PER_PAGE]

    def test_second_page_carries_the_next_releases(self, client):
        response = client.get("/novita/", {"page": 2})

        page = response.context["releases"]
        assert (
            list(page.object_list)
            == RELEASES[RELEASES_PER_PAGE : RELEASES_PER_PAGE * 2]
        )

    def test_out_of_range_page_falls_back_to_the_last_page(self, client):
        response = client.get("/novita/", {"page": 9999})

        assert response.status_code == 200
        page = response.context["releases"]
        assert page.number == page.paginator.num_pages


class TestReleasesData:
    def test_every_entry_is_well_formed(self):
        for entry in RELEASES:
            assert entry["version"]
            assert not entry["version"].startswith("v")
            assert 2 <= len(entry["notes"]) <= 4
            assert all(note.strip() for note in entry["notes"])

    def test_entries_are_ordered_newest_first(self):
        dates = [entry["date"] for entry in RELEASES]
        assert dates == sorted(dates, reverse=True)
