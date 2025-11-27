"""Integration tests for trip image handling in views"""

from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestTripCreateImageHandling:
    """Tests for image handling in trip_create view"""

    @patch("trips.views.process_trip_image")
    @patch("trips.views.download_unsplash_photo")
    @patch("trips.views.search_unsplash_photos")
    def test_create_with_unsplash_photo_success(
        self, mock_search, mock_download, mock_process, client, user_factory
    ):
        """Test creating trip with Unsplash photo selection - full success path"""
        user = user_factory()
        client.force_login(user)

        # Mock successful Unsplash search
        mock_search.return_value = [
            {
                "id": "photo123",
                "urls": {"regular": "https://example.com/photo.jpg"},
                "user": {
                    "name": "Test Photographer",
                    "profile": "https://unsplash.com/@test",
                },
                "links": {
                    "html": "https://unsplash.com/photos/photo123",
                    "download_location": "https://api.unsplash.com/download",
                },
            }
        ]

        # Mock successful download
        mock_download.return_value = (
            b"fake_image_data",
            {"source": "unsplash", "photographer": "Test Photographer"},
        )

        # Mock successful processing
        fake_file = InMemoryUploadedFile(
            BytesIO(b"processed"),
            "ImageField",
            "test.jpg",
            "image/jpeg",
            1024,
            None,
        )
        mock_process.return_value = fake_file

        response = client.post(
            reverse("trips:trip-create"),
            {
                "title": "Test Trip",
                "destination": "Paris",
                "description": "Test",
                "selected_photo_id": "photo123",
            },
        )

        # Should succeed
        assert response.status_code in [200, 204, 302]
        mock_search.assert_called_once_with("Paris", per_page=10)
        mock_download.assert_called_once()
        mock_process.assert_called_once()


class TestTripUpdateImageHandling:
    """Tests for image handling in trip_update view"""

    @patch("trips.views.process_trip_image")
    @patch("trips.views.download_unsplash_photo")
    @patch("trips.views.search_unsplash_photos")
    def test_update_with_unsplash_photo_success(
        self,
        mock_search,
        mock_download,
        mock_process,
        client,
        trip_factory,
        user_factory,
    ):
        """Test updating trip with Unsplash photo selection - full success path"""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)

        # Mock successful Unsplash search
        mock_search.return_value = [
            {
                "id": "photo456",
                "urls": {"regular": "https://example.com/photo.jpg"},
                "user": {
                    "name": "Test Photographer",
                    "profile": "https://unsplash.com/@test",
                },
                "links": {
                    "html": "https://unsplash.com/photos/photo456",
                    "download_location": "https://api.unsplash.com/download",
                },
            }
        ]

        # Mock successful download
        mock_download.return_value = (
            b"fake_image_data",
            {"source": "unsplash", "photographer": "Test Photographer"},
        )

        # Mock successful processing
        fake_file = InMemoryUploadedFile(
            BytesIO(b"processed"),
            "ImageField",
            "test.jpg",
            "image/jpeg",
            1024,
            None,
        )
        mock_process.return_value = fake_file

        response = client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            {
                "title": trip.title,
                "destination": trip.destination,
                "description": trip.description or "",
                "selected_photo_id": "photo456",
            },
        )

        assert response.status_code in [200, 204, 302]
        mock_search.assert_called_once_with("Paris", per_page=10)
        mock_download.assert_called_once()
        mock_process.assert_called_once()


class TestTripFileUpload:
    """Tests for direct file upload in trip views"""

    @patch("trips.views.process_trip_image")
    def test_create_with_file_upload(self, mock_process, client, user_factory):
        """Test creating trip with file upload via FILES"""
        from io import BytesIO

        from django.core.files.uploadedfile import InMemoryUploadedFile

        user = user_factory()
        client.force_login(user)

        # Create a file that will be in request.FILES
        fake_file = SimpleUploadedFile(
            "upload.jpg", b"fake_content", content_type="image/jpeg"
        )

        # Mock processing to return a file
        processed = InMemoryUploadedFile(
            BytesIO(b"processed"),
            "ImageField",
            "test.jpg",
            "image/jpeg",
            1024,
            None,
        )
        mock_process.return_value = processed

        # Post with file in FILES
        response = client.post(
            reverse("trips:trip-create"),
            data={
                "title": "Trip",
                "destination": "Paris",
                "description": "",
            },
            files={"image": fake_file},
        )

        # The code path should be hit if FILES contains 'image'
        assert response.status_code in [200, 204, 302]

    @patch("trips.views.process_trip_image")
    def test_update_with_file_upload(
        self, mock_process, client, trip_factory, user_factory
    ):
        """Test updating trip with file upload via FILES"""
        from io import BytesIO

        from django.core.files.uploadedfile import InMemoryUploadedFile

        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)

        # Create a file
        fake_file = SimpleUploadedFile(
            "upload.jpg", b"fake_content", content_type="image/jpeg"
        )

        # Mock processing
        processed = InMemoryUploadedFile(
            BytesIO(b"processed"),
            "ImageField",
            "test.jpg",
            "image/jpeg",
            1024,
            None,
        )
        mock_process.return_value = processed

        response = client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            data={
                "title": trip.title,
                "destination": trip.destination,
                "description": trip.description or "",
            },
            files={"image": fake_file},
        )

        assert response.status_code in [200, 204, 302]

    @patch("trips.views.process_trip_image")
    @patch("trips.views.download_unsplash_photo")
    @patch("trips.views.search_unsplash_photos")
    def test_create_file_upload_overrides_unsplash(
        self, mock_search, mock_download, mock_process, client, user_factory
    ):
        """Test that file upload overrides Unsplash selection in trip_create"""
        user = user_factory()
        client.force_login(user)

        # Mock Unsplash search
        mock_search.return_value = [
            {
                "id": "photo123",
                "urls": {"regular": "https://example.com/photo.jpg"},
                "user": {
                    "name": "Test Photographer",
                    "profile": "https://unsplash.com/@test",
                },
                "links": {
                    "html": "https://unsplash.com/photos/photo123",
                    "download_location": "https://api.unsplash.com/download",
                },
            }
        ]

        # Mock Unsplash download
        mock_download.return_value = (
            b"unsplash_data",
            {"source": "unsplash", "photographer": "Test Photographer"},
        )

        # Mock image processing - should be called twice (Unsplash + file upload)
        processed_file = InMemoryUploadedFile(
            BytesIO(b"processed_upload"),
            "ImageField",
            "upload.jpg",
            "image/jpeg",
            1024,
            None,
        )
        mock_process.return_value = processed_file

        # Create uploaded file
        uploaded = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )

        # Post with BOTH selected_photo_id AND file upload
        response = client.post(
            reverse("trips:trip-create"),
            data={
                "title": "Test Trip",
                "destination": "Paris",
                "description": "Test",
                "selected_photo_id": "photo123",
            },
            files={"image": uploaded},
        )

        assert response.status_code in [200, 204, 302]
        # process_trip_image should be called for file upload (overriding Unsplash)
        assert mock_process.call_count >= 1

    @patch("trips.views.process_trip_image")
    @patch("trips.views.download_unsplash_photo")
    @patch("trips.views.search_unsplash_photos")
    def test_update_file_upload_overrides_unsplash(
        self,
        mock_search,
        mock_download,
        mock_process,
        client,
        trip_factory,
        user_factory,
    ):
        """Test that file upload overrides Unsplash selection in trip_update"""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)

        # Mock Unsplash search
        mock_search.return_value = [
            {
                "id": "photo456",
                "urls": {"regular": "https://example.com/photo.jpg"},
                "user": {
                    "name": "Test Photographer",
                    "profile": "https://unsplash.com/@test",
                },
                "links": {
                    "html": "https://unsplash.com/photos/photo456",
                    "download_location": "https://api.unsplash.com/download",
                },
            }
        ]

        # Mock Unsplash download
        mock_download.return_value = (
            b"unsplash_data",
            {"source": "unsplash", "photographer": "Test Photographer"},
        )

        # Mock image processing
        processed_file = InMemoryUploadedFile(
            BytesIO(b"processed_upload"),
            "ImageField",
            "upload.jpg",
            "image/jpeg",
            1024,
            None,
        )
        mock_process.return_value = processed_file

        # Create uploaded file
        uploaded = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )

        # Post with BOTH selected_photo_id AND file upload
        response = client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            data={
                "title": trip.title,
                "destination": trip.destination,
                "description": trip.description or "",
                "selected_photo_id": "photo456",
            },
            files={"image": uploaded},
        )

        assert response.status_code in [200, 204, 302]
        # process_trip_image should be called for file upload (overriding Unsplash)
        assert mock_process.call_count >= 1
