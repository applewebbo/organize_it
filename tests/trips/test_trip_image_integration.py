"""Integration tests for trip image handling in views"""

from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.urls import reverse

pytestmark = pytest.mark.django_db


MOCK_PHOTO = {
    "id": "photo123",
    "urls": {"regular": "https://example.com/photo.jpg"},
    "user": {"name": "Test Photographer", "profile": "https://unsplash.com/@test"},
    "links": {
        "html": "https://unsplash.com/photos/photo123",
        "download_location": "https://api.unsplash.com/download",
    },
}


class TestTripCreateImageHandling:
    """Tests for image handling in trip_create view"""

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_create_with_unsplash_fires_async_task(
        self, mock_search, mock_async_task, client, user_factory
    ):
        """Unsplash selection triggers async task instead of blocking download."""
        user = user_factory()
        client.force_login(user)
        mock_search.return_value = [MOCK_PHOTO]

        response = client.post(
            reverse("trips:trip-create"),
            {
                "title": "Test Trip",
                "destination": "Paris",
                "selected_photo_id": "photo123",
            },
        )

        assert response.status_code in [200, 204, 302]
        mock_search.assert_called_once_with("Paris", per_page=10)
        mock_async_task.assert_called_once()
        args = mock_async_task.call_args[0]
        assert args[0] == "trips.tasks.download_trip_unsplash_photo"
        assert args[2] == MOCK_PHOTO

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_create_photo_not_found_in_results_does_not_fire_task(
        self, mock_search, mock_async_task, client, user_factory
    ):
        """If selected_photo_id doesn't match any result, no task is fired."""
        user = user_factory()
        client.force_login(user)
        mock_search.return_value = [MOCK_PHOTO]

        response = client.post(
            reverse("trips:trip-create"),
            {
                "title": "Test Trip",
                "destination": "Paris",
                "selected_photo_id": "nonexistent",
            },
        )

        assert response.status_code in [200, 204, 302]
        mock_async_task.assert_not_called()

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_create_empty_photo_results_does_not_fire_task(
        self, mock_search, mock_async_task, client, user_factory
    ):
        """If Unsplash returns no results, no task is fired."""
        user = user_factory()
        client.force_login(user)
        mock_search.return_value = []

        response = client.post(
            reverse("trips:trip-create"),
            {
                "title": "Test Trip",
                "destination": "Paris",
                "selected_photo_id": "photo123",
            },
        )

        assert response.status_code in [200, 204, 302]
        mock_async_task.assert_not_called()


class TestTripUpdateImageHandling:
    """Tests for image handling in trip_update view"""

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_update_with_unsplash_fires_async_task(
        self, mock_search, mock_async_task, client, trip_factory, user_factory
    ):
        """Unsplash selection in update triggers async task."""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)
        mock_search.return_value = [{**MOCK_PHOTO, "id": "photo456"}]

        response = client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            {
                "title": trip.title,
                "destination": trip.destination,
                "selected_photo_id": "photo456",
            },
        )

        assert response.status_code in [200, 204, 302]
        mock_search.assert_called_once_with("Paris", per_page=10)
        mock_async_task.assert_called_once()
        args = mock_async_task.call_args[0]
        assert args[0] == "trips.tasks.download_trip_unsplash_photo"


class TestTripUpdateImageHandlingExtra:
    """Additional edge-case tests for image handling in trip_update view."""

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_update_empty_photo_results_does_not_fire_task(
        self, mock_search, mock_async_task, client, trip_factory, user_factory
    ):
        """If Unsplash returns no results during update, no task is fired."""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)
        mock_search.return_value = []

        response = client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            {
                "title": trip.title,
                "destination": trip.destination,
                "selected_photo_id": "photo456",
            },
        )

        assert response.status_code in [200, 204, 302]
        mock_async_task.assert_not_called()


class TestTripFileUpload:
    """Tests for direct file upload in trip views"""

    @patch("trips.views.trips.process_trip_image")
    def test_create_with_file_upload(self, mock_process, client, user_factory):
        """Test creating trip with file upload via FILES"""

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
            },
            files={"image": fake_file},
        )

        # The code path should be hit if FILES contains 'image'
        assert response.status_code in [200, 204, 302]

    @patch("trips.views.trips.process_trip_image")
    def test_update_with_file_upload(
        self, mock_process, client, trip_factory, user_factory
    ):
        """Test updating trip with file upload via FILES"""

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
            },
            files={"image": fake_file},
        )

        assert response.status_code in [200, 204, 302]

    @patch("trips.views.trips.async_task")
    def test_create_file_upload_skips_async_task(
        self, mock_async_task, client, user_factory
    ):
        """When a file is uploaded directly, the Unsplash async task is not fired."""
        user = user_factory()
        client.force_login(user)
        uploaded = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )

        response = client.post(
            reverse("trips:trip-create"),
            data={
                "title": "Test Trip",
                "destination": "Paris",
                "selected_photo_id": "photo123",
            },
            files={"image": uploaded},
        )

        assert response.status_code in [200, 204, 302]
        mock_async_task.assert_not_called()

    @patch("trips.views.trips.async_task")
    def test_update_file_upload_skips_async_task(
        self, mock_async_task, client, trip_factory, user_factory
    ):
        """When a file is uploaded directly, the Unsplash async task is not fired."""
        user = user_factory()
        trip = trip_factory(author=user, destination="Paris")
        client.force_login(user)
        uploaded = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )

        response = client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            data={
                "title": trip.title,
                "destination": trip.destination,
                "selected_photo_id": "photo456",
            },
            files={"image": uploaded},
        )

        assert response.status_code in [200, 204, 302]
        mock_async_task.assert_not_called()


class TestTripImagePendingFlag:
    """Tests for the pending image state and HTMX polling endpoint."""

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_create_sets_pending_flag(
        self, mock_search, mock_async_task, client, user_factory
    ):
        """Creating a trip with Unsplash sets image_metadata.pending=True and clears image."""
        user = user_factory()
        client.force_login(user)
        mock_search.return_value = [MOCK_PHOTO]

        client.post(
            reverse("trips:trip-create"),
            {
                "title": "Pending Trip",
                "destination": "Rome",
                "selected_photo_id": "photo123",
            },
        )

        from trips.models import Trip

        trip = Trip.objects.get(title="Pending Trip", author=user)
        assert trip.image_metadata.get("pending") is True
        assert not trip.image

    @patch("trips.views.trips.async_task")
    @patch("trips.views.trips.search_unsplash_photos")
    def test_update_sets_pending_flag_and_clears_old_image(
        self, mock_search, mock_async_task, client, trip_factory, user_factory
    ):
        """Updating a trip with a new Unsplash photo sets pending=True and clears old image."""
        user = user_factory()
        trip = trip_factory(
            author=user, destination="Rome", image_metadata={"source": "upload"}
        )
        client.force_login(user)
        mock_search.return_value = [MOCK_PHOTO]

        client.post(
            reverse("trips:trip-update", kwargs={"pk": trip.pk}),
            {
                "title": trip.title,
                "destination": trip.destination,
                "selected_photo_id": "photo123",
            },
        )

        trip.refresh_from_db()
        assert trip.image_metadata.get("pending") is True
        assert not trip.image

    def test_image_status_pending_returns_spinner(
        self, client, trip_factory, user_factory
    ):
        """Polling endpoint returns spinner when image is still pending."""
        user = user_factory()
        trip = trip_factory(
            author=user, image_metadata={"source": "unsplash", "pending": True}
        )
        client.force_login(user)

        response = client.get(
            reverse("trips:trip-image-status", kwargs={"pk": trip.pk})
        )

        assert response.status_code == 200
        assert b"loading-spinner" in response.content
        assert b"every 3s" in response.content

    def test_image_status_ready_returns_image(self, client, trip_factory, user_factory):
        """Polling endpoint returns image tag (no spinner) when processing is complete."""
        user = user_factory()
        trip = trip_factory(author=user, image_metadata={"source": "unsplash"})
        client.force_login(user)

        response = client.get(
            reverse("trips:trip-image-status", kwargs={"pk": trip.pk})
        )

        assert response.status_code == 200
        assert b"loading-spinner" not in response.content
        assert b"every 3s" not in response.content

    def test_image_status_forbidden_for_other_user(
        self, client, trip_factory, user_factory
    ):
        """Non-owner cannot access the image status endpoint."""
        owner = user_factory()
        other = user_factory()
        trip = trip_factory(
            author=owner, image_metadata={"source": "unsplash", "pending": True}
        )
        client.force_login(other)

        response = client.get(
            reverse("trips:trip-image-status", kwargs={"pk": trip.pk})
        )

        assert response.status_code == 404
