from decimal import Decimal

import pytest

from trips.expenses import ensure_expense_participants
from trips.models import ExpenseParticipant, TripCollaboration

pytestmark = pytest.mark.django_db


def _add_collaborator(trip, name="Anna", user=None):
    return TripCollaboration.objects.create(
        trip=trip,
        user=user,
        participant_name="" if user else name,
        color=TripCollaboration.next_free_color(trip),
        added_by=trip.author,
    )


class TestEnsureExpenseParticipants:
    def test_creates_author_row(self, trip_factory):
        trip = trip_factory()
        ensure_expense_participants(trip)
        author_rows = ExpenseParticipant.objects.filter(
            trip=trip, user=trip.author, collaboration__isnull=True
        )
        assert author_rows.count() == 1

    def test_creates_row_per_collaboration(self, trip_factory):
        trip = trip_factory()
        _add_collaborator(trip, "Anna")
        _add_collaborator(trip, "Bruno")
        ensure_expense_participants(trip)
        # author + 2 collaborators
        assert ExpenseParticipant.objects.filter(trip=trip).count() == 3

    def test_idempotent(self, trip_factory):
        trip = trip_factory()
        _add_collaborator(trip, "Anna")
        ensure_expense_participants(trip)
        ensure_expense_participants(trip)
        assert ExpenseParticipant.objects.filter(trip=trip).count() == 2

    def test_refreshes_name_snapshot(self, trip_factory):
        trip = trip_factory()
        collab = _add_collaborator(trip, "Anna")
        ensure_expense_participants(trip)
        collab.participant_name = "Annabella"
        collab.save()
        ensure_expense_participants(trip)
        participant = ExpenseParticipant.objects.get(trip=trip, collaboration=collab)
        assert participant.name_snapshot == "Annabella"

    def test_refreshes_author_snapshot(self, trip_factory):
        trip = trip_factory()
        ensure_expense_participants(trip)
        trip.author.profile.first_name = "Enrico"
        trip.author.profile.save()
        ensure_expense_participants(trip)
        participant = ExpenseParticipant.objects.get(
            trip=trip, user=trip.author, collaboration__isnull=True
        )
        assert participant.name_snapshot == "Enrico"

    def test_orphan_without_history_is_deleted(self, trip_factory):
        trip = trip_factory()
        collab = _add_collaborator(trip, "Anna")
        ensure_expense_participants(trip)
        collab.delete()
        ensure_expense_participants(trip)
        # only the author remains
        assert ExpenseParticipant.objects.filter(trip=trip).count() == 1

    def test_orphan_with_history_is_deactivated(self, trip_factory, expense_factory):
        trip = trip_factory()
        collab = _add_collaborator(trip, "Anna")
        ensure_expense_participants(trip)
        participant = ExpenseParticipant.objects.get(trip=trip, collaboration=collab)
        expense_factory(trip=trip, payer=participant, amount=Decimal("10.00"))
        collab.delete()
        ensure_expense_participants(trip)
        participant.refresh_from_db()
        assert participant.is_active is False
        assert ExpenseParticipant.objects.filter(trip=trip).count() == 2

    def test_reactivates_when_collaboration_returns(self, trip_factory):
        trip = trip_factory()
        collab = _add_collaborator(trip, "Anna", user=None)
        ensure_expense_participants(trip)
        participant = ExpenseParticipant.objects.get(trip=trip, collaboration=collab)
        participant.is_active = False
        participant.save(update_fields=["is_active"])
        ensure_expense_participants(trip)
        participant.refresh_from_db()
        assert participant.is_active is True
