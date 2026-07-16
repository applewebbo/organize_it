import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from accounts.models import get_profile
from trips.expenses import ensure_expense_participants
from trips.forms import ExpenseSettingsForm, FamilyUnitForm
from trips.models import ExpenseParticipant, FamilyUnit
from trips.utils import editable_trips_qs

EXPENSES_MODIFIED = {"HX-Trigger": "expensesModified"}


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
            context = {"settings_form": ExpenseSettingsForm(instance=trip)}
            context.update(_config_context(trip))
            return TemplateResponse(
                request,
                "trips/expense-settings.html",
                context,
                headers=EXPENSES_MODIFIED,
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
