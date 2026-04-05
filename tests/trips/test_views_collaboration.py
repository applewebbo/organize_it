"""Tests for collaborator management views (issue #263)."""

import pytest
from django.urls import reverse

from trips.models import TripCollaboration

pytestmark = pytest.mark.django_db


class TestSearchUserByEmail:
    def test_empty_email_returns_empty(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": ""})
        assert response.status_code == 200
        assert response.content == b""

    def test_found_user_not_yet_collab(self, client, user_factory, trip_factory):
        owner = user_factory()
        other = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": other.email})
        assert response.status_code == 200
        assert other.email.encode() in response.content

    def test_found_user_already_collab(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": collab.email})
        assert response.status_code == 200
        assert b"Already a collaborator" in response.content

    def test_owner_email_shows_already_collab(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": owner.email})
        assert response.status_code == 200
        assert b"Already a collaborator" in response.content

    def test_email_not_found(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": "nobody@example.com"})
        assert response.status_code == 200
        assert b"No account found" in response.content

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": "x@x.com"})
        assert response.status_code == 404

    def test_unauthenticated_redirects(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"email": "x@x.com"})
        assert response.status_code == 302


class TestAddCollaborator:
    def test_owner_adds_collaborator(self, client, user_factory, trip_factory):
        owner = user_factory()
        new_collab = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": new_collab.email})
        assert response.status_code == 200
        assert TripCollaboration.objects.filter(trip=trip, user=new_collab).exists()

    def test_auto_assigns_next_free_color(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab1 = user_factory()
        collab2 = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab1, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        client.post(url, {"email": collab2.email})
        collab = TripCollaboration.objects.get(trip=trip, user=collab2)
        assert collab.color == "green"

    def test_unknown_email_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": "ghost@example.com"})
        assert response.status_code == 400

    def test_duplicate_collab_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": collab.email})
        assert response.status_code == 400

    def test_adding_owner_as_collab_returns_400(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": owner.email})
        assert response.status_code == 400

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        other = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": other.email})
        assert response.status_code == 404

    def test_response_contains_updated_section(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        new_collab = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": new_collab.email})
        assert response.status_code == 200
        assert b"collaborators-section" in response.content

    def test_response_triggers_collaborators_modified(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        new_collab = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        response = client.post(url, {"email": new_collab.email})
        assert "collaboratorsModified" in response.headers.get("HX-Trigger", "")


class TestRemoveCollaborator:
    def test_owner_removes_collaborator(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:remove-collaborator", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 200
        assert not TripCollaboration.objects.filter(pk=tc.pk).exists()

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(collab)
        url = reverse("trips:remove-collaborator", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_wrong_trip_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip1 = trip_factory(author=owner)
        trip2 = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip1, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:remove-collaborator", args=[trip2.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_response_contains_updated_section(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:remove-collaborator", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 200
        assert b"collaborators-section" in response.content

    def test_response_triggers_collaborators_modified(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:remove-collaborator", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert "collaboratorsModified" in response.headers.get("HX-Trigger", "")
