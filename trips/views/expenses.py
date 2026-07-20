import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from accounts.models import get_profile
from trips.expenses import build_expense_summary, ensure_expense_participants
from trips.forms import ExpenseForm, ExpenseSettingsForm, FamilyUnitForm
from trips.models import (
    Event,
    Expense,
    ExpenseParticipant,
    ExpenseShare,
    FamilyUnit,
    MainTransfer,
    Stay,
)
from trips.utils import accessible_trips_qs, editable_trips_qs

EXPENSES_MODIFIED = {"HX-Trigger": "expensesModified"}


def _user_net(trip, user, summary):
    """The current user's individual net balance, or None if not a participant."""
    participant = trip.expense_participants.filter(
        Q(user=user) | Q(collaboration__user=user)
    ).first()
    if participant is None:
        return None
    data = summary["nets_by_participant"].get(participant.pk)
    return data["net"] if data else None


def _config_context(trip):
    participants = list(
        trip.expense_participants.filter(is_active=True).select_related("family_unit")
    )
    return {
        "trip": trip,
        "units": list(trip.family_units.all()),
        "unassigned": [p for p in participants if p.family_unit_id is None],
        "participants": participants,
    }


def _render_config(request, trip):
    return TemplateResponse(
        request,
        "trips/expense-settings.html#config",
        _config_context(trip),
        headers=EXPENSES_MODIFIED,
    )


@login_required
def expense_settings(request, trip_pk):
    """GET/POST the per-trip expense configuration modal (editors only)."""
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    ensure_expense_participants(trip)

    if request.method == "POST":
        form = ExpenseSettingsForm(request.POST, instance=trip)
        if form.is_valid():
            form.save()
            # Close the modal, refresh the summary card and confirm the save.
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps(
                        {
                            "expensesModified": {},
                            "hide-modal": {},
                            "showMessage": {
                                "type": "success",
                                "message": str(_("Expense settings saved")),
                            },
                        }
                    )
                },
            )
    else:
        initial = {}
        if not trip.expenses_enabled:
            initial["expense_currency"] = get_profile(trip.author).currency
        form = ExpenseSettingsForm(instance=trip, initial=initial)

    context = {"settings_form": form}
    context.update(_config_context(trip))
    return TemplateResponse(request, "trips/expense-settings.html", context)


@login_required
@require_http_methods(["POST"])
def family_unit_create(request, trip_pk):
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    form = FamilyUnitForm(request.POST)
    if form.is_valid():
        unit = form.save(commit=False)
        unit.trip = trip
        unit.save()
    return _render_config(request, trip)


@login_required
@require_http_methods(["POST"])
def family_unit_delete(request, pk):
    unit = get_object_or_404(FamilyUnit, pk=pk)
    trip = get_object_or_404(editable_trips_qs(request.user), pk=unit.trip_id)
    unit.delete()
    return _render_config(request, trip)


@login_required
@require_http_methods(["POST"])
def family_unit_assign(request, trip_pk):
    """Assign a participant to a family unit (or detach).

    Drag & drop posts JSON and expects a 204 (the DOM already moved). The
    mobile ``<select>`` fallback posts form data and gets the refreshed config.
    """
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    is_json = request.content_type == "application/json"
    try:
        if is_json:
            payload = json.loads(request.body)
            participant_id = int(payload["participant_id"])
            unit_id = payload.get("unit_id")
        else:
            participant_id = int(request.POST["participant_id"])
            unit_id = request.POST.get("unit_id") or None
    except ValueError, KeyError, TypeError, json.JSONDecodeError:
        return HttpResponseBadRequest()

    participant = get_object_or_404(ExpenseParticipant, pk=participant_id, trip=trip)
    if unit_id is None:
        participant.family_unit = None
    else:
        participant.family_unit = get_object_or_404(FamilyUnit, pk=unit_id, trip=trip)
    participant.save(update_fields=["family_unit"])

    if is_json:
        return HttpResponse(status=204, headers=EXPENSES_MODIFIED)
    return _render_config(request, trip)


@login_required
@require_http_methods(["POST"])
def participant_toggle_child(request, pk):
    participant = get_object_or_404(ExpenseParticipant, pk=pk)
    trip = get_object_or_404(editable_trips_qs(request.user), pk=participant.trip_id)
    participant.is_child = not participant.is_child
    participant.save(update_fields=["is_child"])
    return _render_config(request, trip)


@login_required
def expenses_card(request, trip_pk):
    """Lazy summary card shown inside the trip detail (any participant)."""
    trip = get_object_or_404(accessible_trips_qs(request.user), pk=trip_pk)
    context = {"trip": trip}
    if trip.expenses_enabled:
        ensure_expense_participants(trip)
        summary = build_expense_summary(trip)
        context["summary"] = summary
        context["user_net"] = _user_net(trip, request.user, summary)
    return TemplateResponse(request, "trips/includes/expenses-card.html", context)


@login_required
@require_http_methods(["POST"])
def expense_toggle(request, trip_pk):
    """Enable/disable expense sharing from the inline card switch (editors only)."""
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    enabling = "expenses_enabled" in request.POST
    if enabling and not trip.expenses_enabled:
        trip.expense_currency = get_profile(trip.author).currency
    trip.expenses_enabled = enabling
    trip.save(update_fields=["expenses_enabled", "expense_currency"])

    context = {"trip": trip}
    if trip.expenses_enabled:
        ensure_expense_participants(trip)
        summary = build_expense_summary(trip)
        context["summary"] = summary
        context["user_net"] = _user_net(trip, request.user, summary)
    return TemplateResponse(request, "trips/includes/expenses-card.html", context)


@login_required
def expenses_modal(request, trip_pk):
    """Detailed expense view (balances, list, totals) in a modal."""
    trip = get_object_or_404(accessible_trips_qs(request.user), pk=trip_pk)
    ensure_expense_participants(trip)
    summary = build_expense_summary(trip)
    expenses = trip.expenses.select_related("payer__family_unit").all()
    return TemplateResponse(
        request,
        "trips/expenses-modal.html",
        {"trip": trip, "summary": summary, "expenses": expenses},
    )


def _resolve_linked(trip, ct, obj_id):
    """Resolve the trip item an expense is attached to from ``ct``/``obj`` params."""
    if not ct or not obj_id:
        return None
    if ct == "event":
        return get_object_or_404(Event, pk=obj_id, trip=trip)
    if ct == "stay":
        return get_object_or_404(
            Stay.objects.filter(days__trip=trip).distinct(), pk=obj_id
        )
    if ct == "transfer":
        return get_object_or_404(MainTransfer, pk=obj_id, trip=trip)
    raise Http404


def _default_date(trip, linked_obj):
    if isinstance(linked_obj, Event):
        return linked_obj.day.date if linked_obj.day else trip.start_date
    if isinstance(linked_obj, Stay):
        first_day = linked_obj.days.first()
        return first_day.date if first_day else trip.start_date
    if isinstance(linked_obj, MainTransfer):
        if linked_obj.direction == MainTransfer.Direction.DEPARTURE:
            return trip.end_date
        return trip.start_date
    return timezone.localdate()


def _save_shares(expense, participant_ids):
    expense.shares.all().delete()
    ExpenseShare.objects.bulk_create(
        ExpenseShare(expense=expense, participant_id=pid) for pid in participant_ids
    )


@login_required
def expense_create(request, trip_pk):
    """Create an expense, optionally linked to an item via ?ct=&obj=."""
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    ensure_expense_participants(trip)
    ct = request.GET.get("ct", "")
    obj_id = request.GET.get("obj", "")
    linked_obj = _resolve_linked(trip, ct, obj_id)
    linked = linked_obj is not None

    if request.method == "POST":
        form = ExpenseForm(request.POST, trip=trip)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.trip = trip
            expense.created_by = request.user
            expense.payer_id = form.payer_participant_id
            if linked:
                expense.content_object = linked_obj
            expense.save()
            _save_shares(expense, form.sharer_participant_ids)
            return HttpResponse(status=204, headers=EXPENSES_MODIFIED)
    else:
        initial = {"date": _default_date(trip, linked_obj)}
        current = trip.expense_participants.filter(
            user=request.user, is_active=True
        ).first()
        form = ExpenseForm(trip=trip, initial=initial, current_participant=current)

    return TemplateResponse(
        request,
        "trips/expense-create.html",
        {"form": form, "trip": trip, "linked_object": linked_obj},
    )


@login_required
def expense_modify(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    trip = get_object_or_404(editable_trips_qs(request.user), pk=expense.trip_id)
    ensure_expense_participants(trip)

    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense, trip=trip)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.payer_id = form.payer_participant_id
            expense.save()
            _save_shares(expense, form.sharer_participant_ids)
            return HttpResponse(status=204, headers=EXPENSES_MODIFIED)
    else:
        form = ExpenseForm(instance=expense, trip=trip)

    return TemplateResponse(
        request,
        "trips/expense-modify.html",
        {"form": form, "trip": trip, "expense": expense},
    )


@login_required
@require_http_methods(["POST"])
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    get_object_or_404(editable_trips_qs(request.user), pk=expense.trip_id)
    expense.delete()
    return HttpResponse(status=204, headers=EXPENSES_MODIFIED)
