import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import get_profile
from suggestions.ai.base import AISuggestionError
from suggestions.services import (
    DAY_STRATEGY_ADD,
    apply_day_itinerary,
    generate_trip_itinerary,
    has_own_ai_key,
    to_stop_card,
)
from trips.forms import WizardBasicsForm
from trips.models import Trip
from trips.utils import apply_stage, process_trip_image

WIZARD_STEP_AI = 2
WIZARD_STEP_STAYS = 3


def _require_wizard_access(user):
    """The creation wizard is offered only to users with their own AI key."""
    if not has_own_ai_key(user):
        raise PermissionDenied


@login_required
@require_http_methods(["GET"])
def wizard_start(request):
    """Render the wizard shell on the Basics step."""
    _require_wizard_access(request.user)
    context = {"form": WizardBasicsForm(), "step": 1}
    return TemplateResponse(request, "trips/wizard/wizard.html", context)


@login_required
@require_http_methods(["POST"])
def wizard_basics(request):
    """Validate the Basics step, create the draft trip with its days and stages,
    then advance to the AI step."""
    _require_wizard_access(request.user)
    form = WizardBasicsForm(request.POST, request.FILES)
    if not form.is_valid():
        context = {"form": form, "step": 1}
        return TemplateResponse(request, "trips/wizard/basics-step.html", context)

    stages = form.cleaned_data["stages_list"]
    main_stage = stages[0]
    trip = Trip(
        author=request.user,
        title=form.cleaned_data["title"],
        destination=main_stage["destination"],
        start_date=form.cleaned_data["start_date"],
        end_date=form.cleaned_data["end_date"],
        wizard_completed=False,
        wizard_step=WIZARD_STEP_AI,
        wizard_started_at=timezone.now(),
    )
    if main_stage.get("latitude") is not None:
        trip.destination_latitude = main_stage["latitude"]
        trip.destination_longitude = main_stage["longitude"]
    if request.FILES.get("image"):  # pragma: no cover
        processed_image = process_trip_image(request.FILES["image"])
        if processed_image:
            trip.image = processed_image
            trip.image_metadata = {"source": "upload"}
    trip.save()

    _assign_stages_to_days(trip, stages)

    context = {"trip": trip, "step": WIZARD_STEP_AI}
    response = TemplateResponse(request, "trips/wizard/ai-step.html", context)
    # Tell the exit guard a recoverable draft now exists (message wording changes).
    response["HX-Trigger"] = "wizard-draft-created"
    return response


def _get_wizard_trip(request, pk):
    """Fetch the caller's own trip for a wizard step, gated on AI access."""
    _require_wizard_access(request.user)
    return get_object_or_404(Trip, pk=pk, author=request.user)


def _build_ai_day_cards(trip, grounded_days):
    """Map grounded days to per-day review cards keyed to the trip's own days."""
    days_by_date = {day.date: day for day in trip.days.all()}
    cards = []
    for grounded_day in grounded_days:
        day = days_by_date.get(grounded_day.date)
        stops = [to_stop_card(stop) for stop in grounded_day.stops]
        cards.append(
            {
                "date_iso": grounded_day.date.isoformat(),
                "number": day.number if day else None,
                "destination": grounded_day.destination,
                "stops": stops,
                "stop_count": len(stops),
            }
        )
    return cards


@login_required
@require_http_methods(["POST"])
def wizard_ai_generate(request, pk):
    """Generate a whole-trip AI itinerary and render it for per-day review."""
    trip = _get_wizard_trip(request, pk)
    force_refresh = bool(request.POST.get("refresh"))
    overrides = {}
    notes = request.POST.get("notes", "").strip()
    if notes:
        overrides["notes"] = notes
    language = get_profile(request.user).language

    days = []
    error_kind = None
    try:
        grounded_days = generate_trip_itinerary(
            request.user, trip, overrides, language, force_refresh
        )
        days = _build_ai_day_cards(trip, grounded_days)
    except AISuggestionError as exc:
        error_kind = exc.kind

    context = {"trip": trip, "days": days, "error_kind": error_kind}
    return TemplateResponse(request, "trips/wizard/ai-results.html", context)


@login_required
@require_http_methods(["POST"])
def wizard_ai_confirm(request, pk):
    """Apply the days the user kept, then advance the wizard to the Stays step."""
    trip = _get_wizard_trip(request, pk)
    try:
        payload = json.loads(request.POST.get("days", "[]"))
    except json.JSONDecodeError:
        payload = []

    days_by_date = {day.date.isoformat(): day for day in trip.days.all()}
    for entry in payload:
        day = days_by_date.get(entry.get("date"))
        stops = entry.get("stops") or []
        if day is None or not stops:
            continue
        apply_day_itinerary(request.user, trip, day, DAY_STRATEGY_ADD, stops)

    trip.wizard_step = WIZARD_STEP_STAYS
    trip.save(update_fields=["wizard_step"])

    context = {"trip": trip, "step": WIZARD_STEP_STAYS}
    return TemplateResponse(request, "trips/wizard/ai-applied.html", context)


@login_required
@require_http_methods(["POST"])
def wizard_finish(request, pk):
    """Mark the wizard draft complete and leave the wizard for the trip."""
    trip = _get_wizard_trip(request, pk)
    trip.wizard_completed = True
    trip.save(update_fields=["wizard_completed"])
    return redirect("trips:trip-detail", pk=trip.pk)


@login_required
@require_http_methods(["POST"])
def wizard_cancel(request, pk):
    """Discard the wizard draft and return home."""
    trip = _get_wizard_trip(request, pk)
    trip.delete()
    return redirect("trips:home")


def _assign_stages_to_days(trip, stages):
    """Assign consecutive days to each stage by its nights. The final stage also
    absorbs the trailing departure day (total days = total nights + 1)."""
    days = list(trip.days.order_by("number"))
    index = 0
    last = len(stages) - 1
    for position, stage in enumerate(stages):
        nights = stage["nights"]
        if position == last:
            slice_days = days[index:]
        else:
            slice_days = days[index : index + nights]
        apply_stage(
            trip,
            [day.pk for day in slice_days],
            stage["destination"],
            stage.get("latitude"),
            stage.get("longitude"),
        )
        index += nights
