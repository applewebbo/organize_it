"""Tests for image-related views"""

from unittest.mock import patch

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestSearchTripImages:
    """Tests for search_trip_images view"""

    @patch("trips.views.search_unsplash_photos")
    def test_search_trip_images_success(
        self, mock_search, client, user_factory, trip_factory
    ):
        """Test successful image search"""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)

        mock_search.return_value = [
            {
                "id": "photo123",
                "urls": {"small": "https://example.com/small.jpg"},
                "user": {"name": "Test User"},
            }
        ]

        response = client.post(
            reverse("trips:search-images"),
            {"destination": "Paris", "trip_id": trip.pk},
            **{"HTTP_HX_REQUEST": "true"},
        )

        assert response.status_code == 200
        assert b"photo123" in response.content
        mock_search.assert_called_once_with("Paris", per_page=3)

    @patch("trips.views.search_unsplash_photos")
    def test_search_trip_images_empty_query(self, mock_search, client, user_factory):
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
        mock_search.assert_not_called()

    @patch("trips.views.search_unsplash_photos")
    def test_search_trip_images_api_error(self, mock_search, client, user_factory):
        """Test search when Unsplash API returns error"""
        user = user_factory()
        client.force_login(user)

        mock_search.return_value = None  # API error

        response = client.post(
            reverse("trips:search-images"),
            {"destination": "Paris", "trip_id": "1"},
            **{"HTTP_HX_REQUEST": "true"},
        )

        assert response.status_code == 200
        assert b"Unsplash API error" in response.content

    @patch("trips.views.search_unsplash_photos")
    def test_search_trip_images_no_results(self, mock_search, client, user_factory):
        """Test search with no results"""
        user = user_factory()
        client.force_login(user)

        mock_search.return_value = []  # No results

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
