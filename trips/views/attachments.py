from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from trips.models import (
    Attachment,
    Event,
    MainTransfer,
    Stay,
    Trip,
)
from trips.utils import accessible_trips_qs

CATEGORY_TO_MODEL = {
    "trip": Trip,
    "main": MainTransfer,
    "stay": Stay,
    "event": Event,
}


def _trip_for_object(obj):
    if isinstance(obj, Trip):
        return obj
    if isinstance(obj, (Event, MainTransfer)):
        return obj.trip
    if isinstance(obj, Stay):
        day = obj.days.select_related("trip").first()
        return day.trip if day else None
    return None


def _user_can_access(user, trip):
    if trip is None:
        return False
    return trip.author_id == user.id or trip.collaborators.filter(pk=user.pk).exists()


def _get_attachment_or_404(pk, user):
    att = get_object_or_404(Attachment.objects.select_related("content_type"), pk=pk)
    trip = _trip_for_object(att.content_object)
    if not _user_can_access(user, trip):
        raise Http404
    return att


def _q_for(ct, ids):
    if not ids:
        return Q(pk__in=[])
    return Q(content_type=ct, object_id__in=list(ids))


def _ids_for_trip(trip):
    stay_ids = list(
        Stay.objects.filter(days__trip=trip).values_list("pk", flat=True).distinct()
    )
    event_ids = list(trip.all_events.values_list("pk", flat=True))
    main_ids = list(trip.main_transfers.values_list("pk", flat=True))
    return stay_ids, event_ids, main_ids


def _group_attachments(trip):
    ct_trip = ContentType.objects.get_for_model(Trip)
    ct_stay = ContentType.objects.get_for_model(Stay)
    ct_event = ContentType.objects.get_for_model(Event)
    ct_main = ContentType.objects.get_for_model(MainTransfer)
    stay_ids, event_ids, main_ids = _ids_for_trip(trip)
    query = (
        _q_for(ct_trip, [trip.pk])
        | _q_for(ct_stay, stay_ids)
        | _q_for(ct_event, event_ids)
        | _q_for(ct_main, main_ids)
    )
    attachments = list(Attachment.objects.filter(query))
    return {
        "trip": [a for a in attachments if a.content_type_id == ct_trip.pk],
        "main": [a for a in attachments if a.content_type_id == ct_main.pk],
        "stay": [a for a in attachments if a.content_type_id == ct_stay.pk],
        "event": [a for a in attachments if a.content_type_id == ct_event.pk],
    }


def _targets_for_category(trip, category):
    if category == "trip":
        return [(trip.pk, _("This trip"))]
    if category == "main":
        return [
            (mt.pk, mt.get_direction_display())
            for mt in trip.main_transfers.order_by("direction")
        ]
    if category == "stay":
        stays = Stay.objects.filter(days__trip=trip).distinct().order_by("name")
        return [(s.pk, s.name) for s in stays]
    if category == "event":
        return [
            (e.pk, e.name)
            for e in trip.all_events.select_related("day").order_by(
                "day__date", "order", "pk"
            )
        ]
    return []


@login_required
def attachments_card(request, trip_pk):
    trip = get_object_or_404(accessible_trips_qs(request.user), pk=trip_pk)
    groups = _group_attachments(trip)
    total = sum(len(v) for v in groups.values())
    category_meta = [
        {
            "key": "trip",
            "label": _("Trip"),
            "icon": "ph-suitcase",
            "attachments": groups["trip"],
            "enabled": bool(_targets_for_category(trip, "trip")),
        },
        {
            "key": "main",
            "label": _("How to Get There"),
            "icon": "ph-airplane",
            "attachments": groups["main"],
            "enabled": bool(_targets_for_category(trip, "main")),
        },
        {
            "key": "stay",
            "label": _("Where to Sleep"),
            "icon": "ph-bed",
            "attachments": groups["stay"],
            "enabled": bool(_targets_for_category(trip, "stay")),
        },
        {
            "key": "event",
            "label": _("Events"),
            "icon": "ph-calendar",
            "attachments": groups["event"],
            "enabled": bool(_targets_for_category(trip, "event")),
        },
    ]
    return TemplateResponse(
        request,
        "trips/includes/attachments-card.html",
        {
            "trip": trip,
            "categories": category_meta,
            "total_count": total,
        },
    )


@login_required
@require_http_methods(["GET"])
def attachment_upload_modal(request, trip_pk, category):
    trip = get_object_or_404(accessible_trips_qs(request.user), pk=trip_pk)
    if category not in CATEGORY_TO_MODEL:
        raise Http404
    targets = _targets_for_category(trip, category)
    object_id = request.GET.get("object_id")
    if object_id:
        try:
            object_id_int = int(object_id)
        except ValueError as exc:
            raise Http404 from exc
        targets = [(pk, label) for pk, label in targets if pk == object_id_int]
        if not targets:
            raise Http404
    return TemplateResponse(
        request,
        "trips/attachments/upload-modal.html",
        {
            "trip": trip,
            "category": category,
            "targets": targets,
        },
    )


@login_required
@require_http_methods(["POST"])
def attachment_upload(request, trip_pk, category):
    trip = get_object_or_404(accessible_trips_qs(request.user), pk=trip_pk)
    model = CATEGORY_TO_MODEL.get(category)
    if model is None:
        raise Http404
    object_id = request.POST.get("object_id")
    if not object_id:
        return HttpResponse(status=400)
    obj = get_object_or_404(model, pk=object_id)
    if _trip_for_object(obj) != trip:
        raise Http404
    uploaded = request.FILES.get("file")
    if not uploaded:
        return HttpResponse(status=400)
    att = Attachment(
        content_object=obj,
        file=uploaded,
        original_name=uploaded.name,
        mime_type=uploaded.content_type or "",
        size=uploaded.size,
        uploaded_by=request.user,
        include_in_pdf=request.POST.get("include_in_pdf") in ("on", "true", "1"),
    )
    try:
        att.full_clean()
    except ValidationError:
        return HttpResponse(status=400)
    att.save()
    return HttpResponse(status=204, headers={"HX-Trigger": "attachmentsModified"})


@login_required
@require_http_methods(["POST", "DELETE"])
def attachment_delete(request, pk):
    att = _get_attachment_or_404(pk, request.user)
    att.file.delete(save=False)
    att.delete()
    return HttpResponse(status=204, headers={"HX-Trigger": "attachmentsModified"})


@login_required
@require_http_methods(["GET"])
@xframe_options_sameorigin
def attachment_stream(request, pk):
    att = _get_attachment_or_404(pk, request.user)
    response = FileResponse(att.file.open("rb"), content_type=att.mime_type)
    response["Content-Disposition"] = f'inline; filename="{att.original_name}"'
    return response


def _attachment_title(att):
    obj = att.content_object
    if isinstance(obj, Trip):
        name = obj.title
    elif isinstance(obj, Stay):
        name = obj.name
    elif isinstance(obj, MainTransfer):
        name = obj.get_direction_display()
    elif isinstance(obj, Event):
        name = obj.name
    else:
        return att.original_name
    siblings = list(
        Attachment.objects.filter(
            content_type=att.content_type, object_id=att.object_id
        )
        .order_by("uploaded_at", "pk")
        .values_list("pk", flat=True)
    )
    if len(siblings) > 1:
        idx = siblings.index(att.pk) + 1
        return f"{name} · {_('Document')} {idx}"
    return name


@login_required
@require_http_methods(["GET"])
def attachment_preview(request, pk):
    att = _get_attachment_or_404(pk, request.user)
    return TemplateResponse(
        request,
        "trips/attachments/preview-modal.html",
        {"attachment": att, "title": _attachment_title(att)},
    )
