"""Expense participant sync and balance/settlement algorithm (issue #379)."""

from trips.models import ExpenseParticipant


def _snapshot_for_user(user) -> str:
    """Best display name for a user, used as a durable fallback snapshot."""
    profile = getattr(user, "profile", None)
    if profile and profile.first_name:
        return profile.first_name
    return user.email


def _has_history(participant: ExpenseParticipant) -> bool:
    """True if the participant is referenced by any expense as payer or sharer."""
    return participant.expenses_paid.exists() or participant.expense_shares.exists()


def ensure_expense_participants(trip) -> None:
    """Idempotently sync ExpenseParticipant rows with the trip's participants.

    Creates the author row (user=author, no collaboration) and one row per
    TripCollaboration, refreshing name snapshots. Participants whose source
    collaboration was removed become orphans: deleted when they carry no
    expense history, otherwise deactivated so history is preserved.
    """
    author = trip.author

    author_participant, created = ExpenseParticipant.objects.get_or_create(
        trip=trip,
        user_id=author.pk,
        collaboration__isnull=True,
        defaults={"name_snapshot": _snapshot_for_user(author)},
    )
    author_snapshot = _snapshot_for_user(author)
    if not created and author_participant.name_snapshot != author_snapshot:
        author_participant.name_snapshot = author_snapshot
        author_participant.save(update_fields=["name_snapshot"])

    existing_by_collab = {
        p.collaboration_id: p
        for p in ExpenseParticipant.objects.filter(
            trip=trip, collaboration__isnull=False
        )
    }

    for collab in trip.collaborations.all():
        participant = existing_by_collab.get(collab.pk)
        name = collab.display_name
        if participant is None:
            ExpenseParticipant.objects.create(
                trip=trip,
                collaboration=collab,
                user=collab.user,
                name_snapshot=name,
            )
        elif participant.name_snapshot != name or not participant.is_active:
            participant.name_snapshot = name
            participant.is_active = True
            participant.save(update_fields=["name_snapshot", "is_active"])

    orphans = ExpenseParticipant.objects.filter(
        trip=trip, collaboration__isnull=True
    ).exclude(user_id=author.pk)
    for orphan in orphans:
        if _has_history(orphan):
            if orphan.is_active:
                orphan.is_active = False
                orphan.save(update_fields=["is_active"])
        else:
            orphan.delete()
