"""Tests for trip sharing via magic links (issue #209)."""

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertTemplateUsed

from trips.models import ShareLink

pytestmark = pytest.mark.django_db


class TestShareLinkModel:
    def test_str(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)
        assert str(link) == f"Share link for {trip.title}"

    def test_is_valid_active_no_expiry(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)
        assert link.is_valid is True

    def test_is_valid_inactive(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user, is_active=False)
        assert link.is_valid is False

    def test_is_valid_expired(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(
            trip=trip,
            created_by=user,
            expires_at=timezone.now() - timedelta(days=1),
        )
        assert link.is_valid is False

    def test_is_valid_not_yet_expired(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(
            trip=trip,
            created_by=user,
            expires_at=timezone.now() + timedelta(days=1),
        )
        assert link.is_valid is True

    def test_uuid_primary_key(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)
        assert isinstance(link.id, uuid.UUID)

    def test_get_absolute_url(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)
        expected = reverse("trips:shared-trip", kwargs={"token": link.id})
        assert link.get_absolute_url() == expected

    def test_cascade_delete_with_trip(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        ShareLink.objects.create(trip=trip, created_by=user)
        assert ShareLink.objects.count() == 1
        trip.delete()
        assert ShareLink.objects.count() == 0

    def test_default_permission_is_view(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)
        assert link.permission_level == ShareLink.PermissionLevel.VIEW

    def test_display_label_uses_label_when_set(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user, label="My label")
        assert link.display_label == "My label"

    def test_display_label_falls_back_to_created_at(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user, label="")
        expected = link.created_at.strftime("%d/%m/%Y %H:%M")
        assert link.display_label == expected


class TestSharedTripDetailView:
    def test_valid_token_shows_trip(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)

        response = client.get(reverse("trips:shared-trip", kwargs={"token": link.id}))

        assert response.status_code == 200
        assertTemplateUsed(response, "trips/shared-trip-detail.html")
        assert response.context["trip"] == trip
        assert response.context["is_shared_view"] is True

    def test_invalid_token_returns_404(self, client):
        response = client.get(
            reverse("trips:shared-trip", kwargs={"token": uuid.uuid4()})
        )
        assert response.status_code == 404

    def test_expired_link_shows_expired_template(
        self, client, user_factory, trip_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(
            trip=trip,
            created_by=user,
            expires_at=timezone.now() - timedelta(days=1),
        )

        response = client.get(reverse("trips:shared-trip", kwargs={"token": link.id}))

        assert response.status_code == 410
        assertTemplateUsed(response, "trips/link-expired.html")

    def test_revoked_link_shows_revoked_template(
        self, client, user_factory, trip_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user, is_active=False)

        response = client.get(reverse("trips:shared-trip", kwargs={"token": link.id}))

        assert response.status_code == 410
        assertTemplateUsed(response, "trips/link-revoked.html")

    def test_no_login_required(self, client, user_factory, trip_factory):
        """Shared view must be accessible without authentication."""
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)

        response = client.get(reverse("trips:shared-trip", kwargs={"token": link.id}))

        assert response.status_code == 200


class TestShareLinkCreateView:
    def test_owner_can_create_link(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)

        response = client.post(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
            data={"label": "My link", "expiration_days": "7"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        assertTemplateUsed(response, "trips/share-link-modal.html")
        assert ShareLink.objects.filter(trip=trip).count() == 1
        assert response.context["created_link"] is not None

    def test_non_owner_cannot_create_link(self, client, user_factory, trip_factory):
        owner = user_factory()
        other_user = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(other_user)

        response = client.post(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
            data={"label": "My link", "expiration_days": "7"},
        )

        assert response.status_code == 404
        assert ShareLink.objects.count() == 0

    def test_unauthenticated_redirects_to_login(
        self, client, user_factory, trip_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)

        response = client.post(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
            data={"label": "My link", "expiration_days": "7"},
        )

        assert response.status_code == 302
        assert "/accounts/login" in response["Location"]

    def test_expiration_7_days_sets_expires_at(
        self, client, user_factory, trip_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)

        client.post(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
            data={"label": "", "expiration_days": "7"},
            HTTP_HX_REQUEST="true",
        )

        link = ShareLink.objects.get(trip=trip)
        assert link.expires_at is not None
        expected = timezone.now() + timedelta(days=7)
        assert abs((link.expires_at - expected).total_seconds()) < 5

    def test_expiration_0_sets_no_expiry(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)

        client.post(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
            data={"label": "", "expiration_days": "0"},
            HTTP_HX_REQUEST="true",
        )

        link = ShareLink.objects.get(trip=trip)
        assert link.expires_at is None

    def test_get_shows_form(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)

        response = client.get(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
        )

        assert response.status_code == 200
        assertTemplateUsed(response, "trips/share-link-modal.html")

    def test_get_includes_existing_links_in_context(
        self, client, user_factory, trip_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        ShareLink.objects.create(trip=trip, created_by=user, label="existing")
        client.force_login(user)

        response = client.get(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
        )

        assert len(response.context["links"]) == 1

    def test_invalid_form_rerenders_modal(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)

        response = client.post(
            reverse("trips:share-link-create", kwargs={"trip_id": trip.id}),
            data={"label": "x" * 101, "expiration_days": "invalid"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        assertTemplateUsed(response, "trips/share-link-modal.html")
        assert ShareLink.objects.count() == 0


class TestShareLinkListView:
    def test_owner_sees_links(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        ShareLink.objects.create(trip=trip, created_by=user, label="Link 1")
        ShareLink.objects.create(trip=trip, created_by=user, label="Link 2")
        client.force_login(user)

        response = client.get(
            reverse("trips:share-link-list", kwargs={"trip_id": trip.id})
        )

        assert response.status_code == 200
        assertTemplateUsed(response, "trips/share-link-list.html")
        assert len(response.context["links"]) == 2

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        other_user = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(other_user)

        response = client.get(
            reverse("trips:share-link-list", kwargs={"trip_id": trip.id})
        )

        assert response.status_code == 404


class TestShareLinkRevokeView:
    def test_owner_can_revoke(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)
        client.force_login(user)

        response = client.post(
            reverse("trips:share-link-revoke", kwargs={"link_id": link.id})
        )

        assert response.status_code == 200
        link.refresh_from_db()
        assert link.is_active is False

    def test_non_owner_cannot_revoke(self, client, user_factory, trip_factory):
        owner = user_factory()
        other_user = user_factory()
        trip = trip_factory(author=owner)
        link = ShareLink.objects.create(trip=trip, created_by=owner)
        client.force_login(other_user)

        response = client.post(
            reverse("trips:share-link-revoke", kwargs={"link_id": link.id})
        )

        assert response.status_code == 404
        link.refresh_from_db()
        assert link.is_active is True

    def test_unauthenticated_redirects(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        link = ShareLink.objects.create(trip=trip, created_by=user)

        response = client.post(
            reverse("trips:share-link-revoke", kwargs={"link_id": link.id})
        )

        assert response.status_code == 302
        link.refresh_from_db()
        assert link.is_active is True


class TestSharedTripWeather:
    def test_shared_view_shows_weather_widget(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        # Add weather data to first day
        day = trip.days.first()
        day.weather_data = {
            "temperature_max": 22.0,
            "temperature_min": 12.0,
            "precipitation_sum": 0.0,
            "wind_speed_max": 15.0,
            "weather_code": 0,
            "weather_icon": "ph-sun",
            "weather_label": "Clear sky",
        }
        day.save()
        link = ShareLink.objects.create(trip=trip, created_by=owner)

        response = client.get(reverse("trips:shared-trip", kwargs={"token": link.id}))

        assert response.status_code == 200
        assert b"ph-sun" in response.content

    def test_shared_view_shows_unavailable_badge_without_weather(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        link = ShareLink.objects.create(trip=trip, created_by=owner)

        response = client.get(reverse("trips:shared-trip", kwargs={"token": link.id}))

        assert response.status_code == 200
        assert b"Forecast unavailable" in response.content
