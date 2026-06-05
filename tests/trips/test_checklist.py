"""Tests for the trip checklist feature (issue #333)."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from trips.models import ChecklistItem, Trip, TripCollaboration
from trips.tasks import send_checklist_reminders

pytestmark = pytest.mark.django_db


class TestChecklistPageAccess:
    def test_author_can_access(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)
        response = client.get(reverse("trips:trip-checklist", args=[trip.pk]))
        assert response.status_code == 200

    def test_collaborator_can_access(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(collab)
        response = client.get(reverse("trips:trip-checklist", args=[trip.pk]))
        assert response.status_code == 200

    def test_stranger_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        response = client.get(reverse("trips:trip-checklist", args=[trip.pk]))
        assert response.status_code == 404

    def test_anonymous_redirects(self, client, user_factory, trip_factory):
        owner = user_factory()
        trip = trip_factory(author=owner)
        response = client.get(reverse("trips:trip-checklist", args=[trip.pk]))
        assert response.status_code == 302


class TestChecklistItemAdd:
    def test_post_creates_item(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)
        url = reverse("trips:checklist-item-add", args=[trip.pk])
        response = client.post(url, {"text": "Buy sunscreen"})
        assert response.status_code == 200
        assert trip.checklist_items.filter(text="Buy sunscreen").exists()

    def test_collaborator_can_add(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(collab)
        url = reverse("trips:checklist-item-add", args=[trip.pk])
        client.post(url, {"text": "Pack passport"})
        assert trip.checklist_items.filter(text="Pack passport").exists()

    def test_empty_text_does_not_create(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)
        url = reverse("trips:checklist-item-add", args=[trip.pk])
        client.post(url, {"text": "   "})
        assert trip.checklist_items.count() == 0

    def test_stranger_gets_404(self, client, user_factory, trip_factory):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        client.force_login(stranger)
        url = reverse("trips:checklist-item-add", args=[trip.pk])
        response = client.post(url, {"text": "Something"})
        assert response.status_code == 404


class TestChecklistItemToggle:
    def test_toggle_to_completed(
        self, client, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        item = checklist_item_factory(trip=trip, completed=False)
        client.force_login(user)
        response = client.put(reverse("trips:checklist-item-toggle", args=[item.pk]))
        item.refresh_from_db()
        assert response.status_code == 200
        assert item.completed is True
        assert item.completed_at is not None

    def test_toggle_back_to_pending(
        self, client, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        item = checklist_item_factory(
            trip=trip, completed=True, completed_at=timezone.now()
        )
        client.force_login(user)
        client.put(reverse("trips:checklist-item-toggle", args=[item.pk]))
        item.refresh_from_db()
        assert item.completed is False
        assert item.completed_at is None

    def test_stranger_cannot_toggle(
        self, client, user_factory, trip_factory, checklist_item_factory
    ):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        item = checklist_item_factory(trip=trip)
        client.force_login(stranger)
        response = client.put(reverse("trips:checklist-item-toggle", args=[item.pk]))
        assert response.status_code == 404


class TestChecklistItemDelete:
    def test_delete_removes_item(
        self, client, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        item = checklist_item_factory(trip=trip)
        client.force_login(user)
        response = client.delete(reverse("trips:checklist-item-delete", args=[item.pk]))
        assert response.status_code == 200
        assert not ChecklistItem.objects.filter(pk=item.pk).exists()

    def test_stranger_cannot_delete(
        self, client, user_factory, trip_factory, checklist_item_factory
    ):
        owner = user_factory()
        stranger = user_factory()
        trip = trip_factory(author=owner)
        item = checklist_item_factory(trip=trip)
        client.force_login(stranger)
        response = client.delete(reverse("trips:checklist-item-delete", args=[item.pk]))
        assert response.status_code == 404
        assert ChecklistItem.objects.filter(pk=item.pk).exists()


class TestChecklistOrdering:
    def test_completed_items_go_last(
        self, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        first = checklist_item_factory(trip=trip, completed=False)
        second = checklist_item_factory(trip=trip, completed=True)
        third = checklist_item_factory(trip=trip, completed=False)
        ordered = list(trip.checklist_items.all())
        assert ordered == [first, third, second]


class TestChecklistBadge:
    def test_trip_detail_shows_badge_counts(
        self, client, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        trip = trip_factory(author=user)
        checklist_item_factory(trip=trip, completed=True)
        checklist_item_factory(trip=trip, completed=False)
        client.force_login(user)
        response = client.get(reverse("trips:trip-detail", args=[trip.pk]))
        assert response.status_code == 200
        assert b"1/2" in response.content

    def test_trip_properties(self, user_factory, trip_factory, checklist_item_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        checklist_item_factory(trip=trip, completed=True)
        checklist_item_factory(trip=trip, completed=False)
        checklist_item_factory(trip=trip, completed=False)
        assert trip.checklist_total == 3
        assert trip.checklist_completed == 1


class TestChecklistReminderSet:
    def test_author_can_set_reminder(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)
        url = reverse("trips:checklist-reminder-set", args=[trip.pk])
        response = client.post(url, {"reminder_days": "7"})
        trip.refresh_from_db()
        assert response.status_code == 200
        assert trip.checklist_reminder_days == 7

    def test_setting_reminder_resets_sent_at(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        trip.checklist_reminder_sent_at = date.today()
        trip.save()
        client.force_login(user)
        url = reverse("trips:checklist-reminder-set", args=[trip.pk])
        client.post(url, {"reminder_days": "3"})
        trip.refresh_from_db()
        assert trip.checklist_reminder_sent_at is None

    def test_off_disables_reminder(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user, checklist_reminder_days=7)
        client.force_login(user)
        url = reverse("trips:checklist-reminder-set", args=[trip.pk])
        client.post(url, {"reminder_days": ""})
        trip.refresh_from_db()
        assert trip.checklist_reminder_days is None

    def test_collaborator_cannot_set_reminder(self, client, user_factory, trip_factory):
        owner = user_factory()
        collab = user_factory()
        trip = trip_factory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        client.force_login(collab)
        url = reverse("trips:checklist-reminder-set", args=[trip.pk])
        response = client.post(url, {"reminder_days": "7"})
        assert response.status_code == 404

    def test_invalid_value_does_not_change(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user, checklist_reminder_days=7)
        client.force_login(user)
        url = reverse("trips:checklist-reminder-set", args=[trip.pk])
        response = client.post(url, {"reminder_days": "999"})
        trip.refresh_from_db()
        assert response.status_code == 200
        assert trip.checklist_reminder_days == 7

    def test_success_returns_message_toast(self, client, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(author=user)
        client.force_login(user)
        url = reverse("trips:checklist-reminder-set", args=[trip.pk])
        response = client.post(
            url, {"reminder_days": "7"}, headers={"HX-Request": "true"}
        )
        assert (
            b"Promemoria salvato" in response.content
            or b"Reminder saved" in response.content
        )
        assert b'id="messages"' in response.content


class TestSendChecklistRemindersTask:
    def _make_trip_with_pending(
        self, user_factory, trip_factory, checklist_item_factory, days_before, **kw
    ):
        user = user_factory()
        start = date.today() + timedelta(days=days_before)
        end = start + timedelta(days=3)
        trip = trip_factory(
            author=user,
            start_date=start,
            end_date=end,
            checklist_reminder_days=days_before,
            **kw,
        )
        checklist_item_factory(trip=trip, completed=False)
        return trip

    def test_sends_email_on_trigger_day(
        self, user_factory, trip_factory, checklist_item_factory
    ):
        trip = self._make_trip_with_pending(
            user_factory, trip_factory, checklist_item_factory, days_before=7
        )
        send_checklist_reminders()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [trip.author.email]

    def test_marks_as_sent(self, user_factory, trip_factory, checklist_item_factory):
        trip = self._make_trip_with_pending(
            user_factory, trip_factory, checklist_item_factory, days_before=3
        )
        send_checklist_reminders()
        trip.refresh_from_db()
        assert trip.checklist_reminder_sent_at == date.today()

    def test_does_not_send_if_no_pending(
        self, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        start = date.today() + timedelta(days=7)
        trip = trip_factory(
            author=user,
            start_date=start,
            end_date=start + timedelta(days=3),
            checklist_reminder_days=7,
        )
        checklist_item_factory(trip=trip, completed=True)
        send_checklist_reminders()
        assert len(mail.outbox) == 0

    def test_does_not_send_twice_same_day(
        self, user_factory, trip_factory, checklist_item_factory
    ):
        trip = self._make_trip_with_pending(
            user_factory, trip_factory, checklist_item_factory, days_before=7
        )
        Trip.objects.filter(pk=trip.pk).update(checklist_reminder_sent_at=date.today())
        send_checklist_reminders()
        assert len(mail.outbox) == 0

    def test_does_not_send_if_wrong_day(
        self, user_factory, trip_factory, checklist_item_factory
    ):
        # reminder_days=7 but departure is in 5 days -> not today's trigger
        user = user_factory()
        start = date.today() + timedelta(days=5)
        trip = trip_factory(
            author=user,
            start_date=start,
            end_date=start + timedelta(days=3),
            checklist_reminder_days=7,
        )
        checklist_item_factory(trip=trip, completed=False)
        send_checklist_reminders()
        assert len(mail.outbox) == 0

    def test_skips_trips_without_reminder(
        self, user_factory, trip_factory, checklist_item_factory
    ):
        user = user_factory()
        start = date.today() + timedelta(days=7)
        trip = trip_factory(
            author=user,
            start_date=start,
            end_date=start + timedelta(days=3),
            checklist_reminder_days=None,
        )
        checklist_item_factory(trip=trip, completed=False)
        send_checklist_reminders()
        assert len(mail.outbox) == 0


class TestChecklistItemModel:
    def test_str(self, user_factory, trip_factory, checklist_item_factory):
        user = user_factory()
        trip = trip_factory(author=user, title="My Trip")
        item = checklist_item_factory(trip=trip, text="Buy something")
        assert "Buy something" in str(item)
        assert "My Trip" in str(item)
