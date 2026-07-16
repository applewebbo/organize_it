"""Expense participant sync and balance/settlement algorithm (issue #379)."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from django.db.models import Sum

from trips.models import Expense, ExpenseParticipant

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Participant:
    """Lightweight, DB-free descriptor used by the pure balance functions."""

    id: int
    is_child: bool = False
    unit_id: int | None = None
    unit_shared: bool = False


@dataclass(frozen=True)
class ExpenseInput:
    """A single expense reduced to what the balance math needs."""

    amount: Decimal
    payer_id: int
    sharer_ids: tuple


def split_amount(amount: Decimal, n: int) -> list[Decimal]:
    """Split an amount into n cent-exact parts using the largest-remainder rule.

    Base parts are floored to the cent; the leftover cents are handed to the
    first slots. The returned parts always sum back to ``amount``.
    """
    if n <= 0:
        return []
    base = (amount / n).quantize(CENT, rounding=ROUND_FLOOR)
    leftover = amount - base * n
    extra_cents = int((leftover / CENT).to_integral_value())
    return [base + (CENT if i < extra_cents else ZERO) for i in range(n)]


def compute_balances(participants, expenses):
    """Return per-participant paid/owed/net plus unattributable-child warnings.

    Children with a family unit that has at least one adult have both their
    consumed shares and any amounts they paid moved onto the unit's adults
    (split evenly), so they drop out of the balance. Children without a usable
    unit keep their own share and are reported as warnings.
    """
    paid = defaultdict(lambda: ZERO)
    owed = defaultdict(lambda: ZERO)
    for expense in expenses:
        paid[expense.payer_id] += expense.amount
        sharers = sorted(expense.sharer_ids)
        for pid, part in zip(
            sharers, split_amount(expense.amount, len(sharers)), strict=True
        ):
            owed[pid] += part

    adults_by_unit = defaultdict(list)
    for participant in participants:
        if not participant.is_child and participant.unit_id is not None:
            adults_by_unit[participant.unit_id].append(participant.id)

    warnings = set()
    for participant in participants:
        if not participant.is_child:
            continue
        adults = sorted(adults_by_unit.get(participant.unit_id, []))
        if not adults:
            warnings.add(participant.id)
            continue
        moved_owed = owed.pop(participant.id, ZERO)
        for aid, part in zip(
            adults, split_amount(moved_owed, len(adults)), strict=True
        ):
            owed[aid] += part
        moved_paid = paid.pop(participant.id, ZERO)
        for aid, part in zip(
            adults, split_amount(moved_paid, len(adults)), strict=True
        ):
            paid[aid] += part

    balances = {}
    for participant in participants:
        if participant.is_child and participant.id not in warnings:
            continue
        pd = paid.get(participant.id, ZERO)
        od = owed.get(participant.id, ZERO)
        balances[participant.id] = {"paid": pd, "owed": od, "net": pd - od}
    return balances, warnings


def aggregate_wallets(participants, balances):
    """Group participant nets into wallets (shared units vs. individuals)."""
    by_id = {p.id: p for p in participants}
    wallet_nets = defaultdict(lambda: ZERO)
    wallet_members = defaultdict(list)
    for pid, balance in balances.items():
        participant = by_id[pid]
        if participant.unit_id is not None and participant.unit_shared:
            key = ("unit", participant.unit_id)
        else:
            key = ("solo", pid)
        wallet_nets[key] += balance["net"]
        wallet_members[key].append(pid)
    return dict(wallet_nets), dict(wallet_members)


def settle(wallet_nets):
    """Greedy minimal settlement between wallets (largest debtor ↔ creditor)."""
    debtors = [[key, -net] for key, net in wallet_nets.items() if net < 0]
    creditors = [[key, net] for key, net in wallet_nets.items() if net > 0]
    debtors.sort(key=lambda item: (-item[1], item[0]))
    creditors.sort(key=lambda item: (-item[1], item[0]))

    settlements = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor_key, debt = debtors[i]
        creditor_key, credit = creditors[j]
        pay = min(debt, credit)
        settlements.append({"from": debtor_key, "to": creditor_key, "amount": pay})
        debtors[i][1] -= pay
        creditors[j][1] -= pay
        if debtors[i][1] == ZERO:
            i += 1
        if creditors[j][1] == ZERO:
            j += 1
    return settlements


def _load_participants(trip):
    descriptors = []
    for participant in trip.expense_participants.select_related("family_unit").all():
        unit = participant.family_unit
        descriptors.append(
            Participant(
                id=participant.pk,
                is_child=participant.is_child,
                unit_id=participant.family_unit_id,
                unit_shared=bool(unit and unit.shared_wallet),
            )
        )
    return descriptors


def _load_expenses(trip):
    inputs = []
    for expense in trip.expenses.prefetch_related("shares").all():
        sharer_ids = tuple(share.participant_id for share in expense.shares.all())
        if not sharer_ids:
            continue
        inputs.append(
            ExpenseInput(
                amount=expense.amount,
                payer_id=expense.payer_id,
                sharer_ids=sharer_ids,
            )
        )
    return inputs


def trip_total(trip) -> Decimal:
    return trip.expenses.aggregate(total=Sum("amount"))["total"] or ZERO


def totals_by_category(trip):
    labels = dict(Expense.Category.choices)
    rows = (
        trip.expenses.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [
        {
            "category": row["category"],
            "label": labels[row["category"]],
            "total": row["total"],
        }
        for row in rows
    ]


def totals_by_day(trip):
    day_numbers = {day.date: day.number for day in trip.days.all()}
    rows = trip.expenses.values("date").annotate(total=Sum("amount")).order_by("date")
    return [
        {
            "date": row["date"],
            "day_number": day_numbers.get(row["date"]),
            "total": row["total"],
        }
        for row in rows
    ]


def build_expense_summary(trip):
    """Assemble the full context used by the expenses card and detail modal."""
    participants = list(trip.expense_participants.select_related("family_unit").all())
    by_id = {p.pk: p for p in participants}
    descriptors = _load_participants(trip)
    expenses = _load_expenses(trip)

    balances, warning_ids = compute_balances(descriptors, expenses)
    wallet_nets, wallet_members = aggregate_wallets(descriptors, balances)
    settlements = settle(wallet_nets)

    def wallet_label(key):
        kind, ident = key
        if kind == "unit":
            # A ("unit", ...) wallet always has at least one member carrying the unit.
            return by_id[wallet_members[key][0]].family_unit.display_name
        return by_id[ident].display_name

    settlement_rows = [
        {
            "from_label": wallet_label(s["from"]),
            "to_label": wallet_label(s["to"]),
            "amount": s["amount"],
        }
        for s in settlements
    ]

    balance_rows = [
        {
            "participant": by_id[pid],
            "paid": data["paid"],
            "owed": data["owed"],
            "net": data["net"],
        }
        for pid, data in balances.items()
    ]
    balance_rows.sort(key=lambda row: row["participant"].display_name.lower())

    return {
        "currency": trip.expense_currency,
        "total": trip_total(trip),
        "settlements": settlement_rows,
        "balances": balance_rows,
        "warnings": [by_id[pid] for pid in warning_ids],
        "by_day": totals_by_day(trip),
        "by_category": totals_by_category(trip),
        "nets_by_participant": balances,
    }


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
