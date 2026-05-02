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
        response = client.get(url, {"collab_email": ""})
        assert response.status_code == 200
        assert response.content == b""

    def test_found_user_not_yet_collab(self, client, user_factory, trip_factory):
        owner = user_factory()
        other = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"collab_email": other.email})
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
        response = client.get(url, {"collab_email": collab.email})
        assert response.status_code == 200
        assert b"Already a participant" in response.content

    def test_owner_email_shows_already_collab(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"collab_email": owner.email})
        assert response.status_code == 200
        assert b"Already a participant" in response.content

    def test_email_not_found(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"collab_email": "nobody@example.com"})
        assert response.status_code == 200
        assert b"No account found" in response.content

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"collab_email": "x@x.com"})
        assert response.status_code == 404

    def test_unauthenticated_redirects(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        url = reverse("trips:search-user-by-email", args=[trip.pk])
        response = client.get(url, {"collab_email": "x@x.com"})
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
        assert b"collab-modal-list" in response.content

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
        assert b"collab-modal-list" in response.content

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


class TestToggleParticipantRole:
    def test_owner_toggles_editor_to_viewer(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner, can_edit=True
        )
        client.force_login(owner)
        url = reverse("trips:toggle-participant-role", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 200
        tc.refresh_from_db()
        assert tc.can_edit is False

    def test_viewer_to_editor_upgrade_not_allowed(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner, can_edit=False
        )
        client.force_login(owner)
        url = reverse("trips:toggle-participant-role", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 400
        tc.refresh_from_db()
        assert tc.can_edit is False

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        tc = TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(collab)
        url = reverse("trips:toggle-participant-role", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert response.status_code == 404

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
        url = reverse("trips:toggle-participant-role", args=[trip.pk, tc.pk])
        response = client.post(url)
        assert "collaboratorsModified" in response.headers.get("HX-Trigger", "")


class TestAddViewerByEmail:
    def test_owner_adds_viewer_unregistered(
        self, client, user_factory, trip_factory, mailoutbox
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-viewer-by-email", args=[trip.pk])
        response = client.post(url, {"email": "viewer@example.com"})
        assert response.status_code == 200
        assert trip.collaborations.filter(
            participant_email="viewer@example.com", can_edit=False
        ).exists()
        collab = trip.collaborations.get(participant_email="viewer@example.com")
        assert collab.share_link is not None
        assert len(mailoutbox) == 1

    def test_owner_adds_viewer_registered(
        self, client, user_factory, trip_factory, mailoutbox
    ):
        owner = user_factory()
        viewer = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-viewer-by-email", args=[trip.pk])
        response = client.post(url, {"email": viewer.email})
        assert response.status_code == 200
        collab = trip.collaborations.get(user=viewer)
        assert collab.can_edit is False
        assert collab.share_link is not None
        assert len(mailoutbox) == 1

    def test_duplicate_email_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-viewer-by-email", args=[trip.pk])
        client.post(url, {"email": "viewer@example.com"})
        response = client.post(url, {"email": "viewer@example.com"})
        assert response.status_code == 400

    def test_empty_email_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-viewer-by-email", args=[trip.pk])
        response = client.post(url, {"email": ""})
        assert response.status_code == 400

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        other = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(other)
        url = reverse("trips:add-viewer-by-email", args=[trip.pk])
        response = client.post(url, {"email": "viewer@example.com"})
        assert response.status_code == 404

    def test_existing_collab_user_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:add-viewer-by-email", args=[trip.pk])
        response = client.post(url, {"email": collab.email})
        assert response.status_code == 400

    def test_remove_viewer_also_deletes_share_link(
        self, client, user_factory, trip_factory
    ):
        from trips.models import ShareLink

        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        client.post(
            reverse("trips:add-viewer-by-email", args=[trip.pk]),
            {"email": "v@example.com"},
        )
        collab = trip.collaborations.get(participant_email="v@example.com")
        link_pk = collab.share_link.pk
        client.post(reverse("trips:remove-collaborator", args=[trip.pk, collab.pk]))
        assert not ShareLink.objects.filter(pk=link_pk).exists()


class TestAddNamedParticipant:
    def test_owner_adds_named_participant(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-named-participant", args=[trip.pk])
        response = client.post(url, {"name": "Marco"})
        assert response.status_code == 200
        assert trip.collaborations.filter(
            participant_name="Marco", can_edit=False, user=None
        ).exists()

    def test_empty_name_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-named-participant", args=[trip.pk])
        response = client.post(url, {"name": ""})
        assert response.status_code == 400

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        other = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(other)
        url = reverse("trips:add-named-participant", args=[trip.pk])
        response = client.post(url, {"name": "Lucia"})
        assert response.status_code == 404

    def test_is_named_only_property(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        client.post(
            reverse("trips:add-named-participant", args=[trip.pk]), {"name": "Lucia"}
        )
        collab = trip.collaborations.get(participant_name="Lucia")
        assert collab.is_named_only is True

    def test_response_triggers_collaborators_modified(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-named-participant", args=[trip.pk])
        response = client.post(url, {"name": "Luca"})
        assert "collaboratorsModified" in response.headers.get("HX-Trigger", "")


class TestCollaboratorsModal:
    def test_owner_sees_modal(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:collaborators-modal", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert b"collab-modal-list" in response.content

    def test_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:collaborators-modal", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 404

    def test_unauthenticated_redirects(self, client, trip_factory, user_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        url = reverse("trips:collaborators-modal", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 302


class TestCollabInline:
    def test_owner_sees_inline(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:collab-inline", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert b"collab-inline" in response.content

    def test_collaborator_sees_inline(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(collab)
        url = reverse("trips:collab-inline", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_stranger_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:collab-inline", args=[trip.pk])
        response = client.get(url)
        assert response.status_code == 404
