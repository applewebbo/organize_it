"""Tests for collaboration email notifications (issue #265)."""

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from trips.models import TripCollaboration, TripInvitation

pytestmark = pytest.mark.django_db


class TestAddCollaboratorEmailNotification:
    def test_email_sent_to_new_collaborator(self, client, user_factory, trip_factory):
        owner = user_factory()
        new_collab = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        client.post(url, {"email": new_collab.email})
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [new_collab.email]

    def test_email_contains_trip_link(self, client, user_factory, trip_factory):
        owner = user_factory()
        new_collab = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        client.post(url, {"email": new_collab.email})
        assert reverse("trips:trip-detail", args=[trip.pk]) in mail.outbox[0].body

    def test_email_mentions_trip_title(self, client, user_factory, trip_factory):
        owner = user_factory()
        new_collab = user_factory()
        trip = trip_factory(author=owner, title="My Test Trip")
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        client.post(url, {"email": new_collab.email})
        assert "My Test Trip" in mail.outbox[0].body

    def test_no_email_on_duplicate_collab(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(owner)
        url = reverse("trips:add-collaborator", args=[trip.pk])
        client.post(url, {"email": collab.email})
        assert len(mail.outbox) == 0


class TestInviteCollaborator:
    def test_invite_creates_invitation(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:invite-collaborator", args=[trip.pk])
        response = client.post(url, {"email": "newuser@example.com"})
        assert response.status_code == 200
        assert TripInvitation.objects.filter(
            trip=trip, email="newuser@example.com"
        ).exists()

    def test_invite_sends_email(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:invite-collaborator", args=[trip.pk])
        client.post(url, {"email": "newuser@example.com"})
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["newuser@example.com"]

    def test_invite_email_contains_accept_link(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:invite-collaborator", args=[trip.pk])
        client.post(url, {"email": "newuser@example.com"})
        invitation = TripInvitation.objects.get(trip=trip, email="newuser@example.com")
        assert str(invitation.token) in mail.outbox[0].body

    def test_invite_non_owner_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:invite-collaborator", args=[trip.pk])
        response = client.post(url, {"email": "newuser@example.com"})
        assert response.status_code == 404

    def test_invite_registered_user_returns_400(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        existing_user = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(owner)
        url = reverse("trips:invite-collaborator", args=[trip.pk])
        response = client.post(url, {"email": existing_user.email})
        assert response.status_code == 400


class TestAcceptInvitation:
    def _make_invitation(self, trip, email, invited_by):
        return TripInvitation.objects.create(
            trip=trip,
            email=email,
            invited_by=invited_by,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )

    def test_accept_creates_collaboration(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        new_user = user_factory(email="invited@example.com")
        invitation = self._make_invitation(trip, new_user.email, owner)
        client.force_login(new_user)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        client.get(url)
        assert TripCollaboration.objects.filter(trip=trip, user=new_user).exists()

    def test_accept_marks_invitation_accepted(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        new_user = user_factory(email="invited@example.com")
        invitation = self._make_invitation(trip, new_user.email, owner)
        client.force_login(new_user)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        client.get(url)
        invitation.refresh_from_db()
        assert invitation.is_accepted

    def test_accept_sends_email_to_owner(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        new_user = user_factory(email="invited@example.com")
        invitation = self._make_invitation(trip, new_user.email, owner)
        client.force_login(new_user)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        client.get(url)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [owner.email]

    def test_accept_email_mentions_new_collaborator(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        new_user = user_factory(email="invited@example.com")
        invitation = self._make_invitation(trip, new_user.email, owner)
        client.force_login(new_user)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        client.get(url)
        assert "invited@example.com" in mail.outbox[0].body

    def test_expired_token_returns_400(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        new_user = user_factory(email="invited@example.com")
        invitation = TripInvitation.objects.create(
            trip=trip,
            email=new_user.email,
            invited_by=owner,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        client.force_login(new_user)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        response = client.get(url)
        assert response.status_code == 400

    def test_already_accepted_token_returns_400(
        self, client, user_factory, trip_factory
    ):
        owner = user_factory()
        trip = trip_factory(author=owner)
        new_user = user_factory(email="invited@example.com")
        invitation = self._make_invitation(trip, new_user.email, owner)
        invitation.is_accepted = True
        invitation.accepted_at = timezone.now()
        invitation.save()
        client.force_login(new_user)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        response = client.get(url)
        assert response.status_code == 400

    def test_unauthenticated_redirects(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        invitation = self._make_invitation(trip, "invited@example.com", owner)
        url = reverse("trips:accept-invitation", kwargs={"token": invitation.token})
        response = client.get(url)
        assert response.status_code == 302
