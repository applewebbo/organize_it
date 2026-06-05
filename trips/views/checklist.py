from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from trips.forms import ChecklistItemForm, ChecklistReminderForm
from trips.models import ChecklistItem, Trip
from trips.utils import accessible_trips_qs, editable_trips_qs


@login_required
def trip_checklist(request, pk):
    trip = get_object_or_404(accessible_trips_qs(request.user), pk=pk)
    items = trip.checklist_items.all()
    is_author = trip.author == request.user
    reminder_form = ChecklistReminderForm(
        initial={"reminder_days": trip.checklist_reminder_days or ""}
    )
    return TemplateResponse(
        request,
        "trips/checklist.html",
        {
            "trip": trip,
            "items": items,
            "add_form": ChecklistItemForm(),
            "reminder_form": reminder_form,
            "is_author": is_author,
        },
    )


@login_required
@require_http_methods(["POST"])
def checklist_item_add(request, trip_pk):
    trip = get_object_or_404(editable_trips_qs(request.user), pk=trip_pk)
    form = ChecklistItemForm(request.POST)
    if form.is_valid() and form.cleaned_data["text"].strip():
        ChecklistItem.objects.create(trip=trip, text=form.cleaned_data["text"].strip())
    items = trip.checklist_items.all()
    return TemplateResponse(
        request,
        "trips/includes/checklist-list.html",
        {"trip": trip, "items": items},
        headers={"HX-Trigger": "checklistModified"},
    )


@login_required
@require_http_methods(["PUT"])
def checklist_item_toggle(request, pk):
    item = get_object_or_404(
        ChecklistItem, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    item.completed = not item.completed
    item.completed_at = timezone.now() if item.completed else None
    item.save()
    items = item.trip.checklist_items.all()
    return TemplateResponse(
        request,
        "trips/includes/checklist-list.html",
        {"trip": item.trip, "items": items},
        headers={"HX-Trigger": "checklistModified"},
    )


@login_required
@require_http_methods(["DELETE"])
def checklist_item_delete(request, pk):
    item = get_object_or_404(
        ChecklistItem, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    trip = item.trip
    item.delete()
    items = trip.checklist_items.all()
    return TemplateResponse(
        request,
        "trips/includes/checklist-list.html",
        {"trip": trip, "items": items},
        headers={"HX-Trigger": "checklistModified"},
    )


@login_required
@require_http_methods(["POST"])
def checklist_reminder_set(request, trip_pk):
    trip = get_object_or_404(Trip, pk=trip_pk, author=request.user)
    form = ChecklistReminderForm(request.POST)
    if form.is_valid():
        days = form.cleaned_data["reminder_days"]
        trip.checklist_reminder_days = int(days) if days else None
        trip.checklist_reminder_sent_at = None
        trip.save(
            update_fields=["checklist_reminder_days", "checklist_reminder_sent_at"]
        )
        messages.success(request, _("Reminder saved"))
    reminder_form = ChecklistReminderForm(
        initial={"reminder_days": trip.checklist_reminder_days or ""}
    )
    return TemplateResponse(
        request,
        "trips/includes/checklist-reminder-card.html",
        {"trip": trip, "reminder_form": reminder_form},
    )
