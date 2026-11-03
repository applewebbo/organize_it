"""Tests for image-related views"""

from unittest.mock import patch

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestSearchTripImages:
    """Tests for search_trip_images view"""

    @patch("trips.views.trips.search_wikimedia_photos")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_search_trip_images_success(
        self, mock_unsplash, mock_wikimedia, client, user_factory, trip_factory
    ):
        """Test successful image search queries and shows both sources"""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)

        mock_unsplash.return_value = [
            {
                "id": "photo123",
                "urls": {"small": "https://example.com/small.jpg"},
                "user": {"name": "Test User"},
                "source": "unsplash",
            }
        ]
        mock_wikimedia.return_value = [
            {
                "id": "wikimedia_456",
                "urls": {"small": "https://example.com/wiki-small.jpg"},
                "user": {"name": "Wiki User"},
                "source": "wikimedia",
            }
        ]

        response = client.post(
            reverse("trips:search-images"),
            {"destination": "Paris", "trip_id": trip.pk},
            **{"HTTP_HX_REQUEST": "true"},
        )

        assert response.status_code == 200
        assert b"photo123" in response.content
        assert b"wikimedia_456" in response.content
        assert b"Wikimedia Commons" in response.content
        mock_unsplash.assert_called_once_with("Paris", per_page=5)
        mock_wikimedia.assert_called_once_with("Paris", per_page=5)

    @patch("trips.views.trips.search_wikimedia_photos")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_search_trip_images_empty_query(
        self, mock_unsplash, mock_wikimedia, client, user_factory
    ):
        """Test search with empty destination"""
        user = user_factory()
        client.force_login(user)

        response = client.post(
            reverse("trips:search-images"),
            {"destination": "", "trip_id": "1"},
            **{"HTTP_HX_REQUEST": "true"},
        )

        assert response.status_code == 200
        assert b"Please enter a destination first" in response.content
        mock_unsplash.assert_not_called()
        mock_wikimedia.assert_not_called()

    @patch("trips.views.trips.search_wikimedia_photos")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_search_trip_images_unsplash_fails_wikimedia_fallback(
        self, mock_unsplash, mock_wikimedia, client, user_factory
    ):
        """When Unsplash errors out, Wikimedia results are still shown"""
        user = user_factory()
        client.force_login(user)

        mock_unsplash.return_value = None  # API error
        mock_wikimedia.return_value = [
            {
                "id": "wikimedia_789",
                "urls": {"small": "https://example.com/wiki-small.jpg"},
                "user": {"name": "Wiki User"},
                "source": "wikimedia",
            }
        ]

        response = client.post(
            reverse("trips:search-images"),
            {"destination": "A small village", "trip_id": "1"},
            **{"HTTP_HX_REQUEST": "true"},
        )

        assert response.status_code == 200
        assert b"wikimedia_789" in response.content

    @patch("trips.views.trips.search_wikimedia_photos")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_search_trip_images_no_results_from_any_source(
        self, mock_unsplash, mock_wikimedia, client, user_factory
    ):
        """Test search with no results from either source"""
        user = user_factory()
        client.force_login(user)

        mock_unsplash.return_value = []
        mock_wikimedia.return_value = []

        response = client.post(
            reverse("trips:search-images"),
            {"destination": "NonExistentPlace", "trip_id": "1"},
            **{"HTTP_HX_REQUEST": "true"},
        )

        assert response.status_code == 200
        assert b"No images found" in response.content

    def test_search_trip_images_wrong_method(self, client, user_factory):
        """Test search with GET method (should be POST)"""
        user = user_factory()
        client.force_login(user)

        response = client.get(reverse("trips:search-images"))

        assert response.status_code == 405
