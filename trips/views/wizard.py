from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from suggestions.services import has_own_ai_key
from trips.forms import WizardBasicsForm
from trips.models import Trip
from trips.utils import apply_stage, process_trip_image

WIZARD_STEP_AI = 2


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
