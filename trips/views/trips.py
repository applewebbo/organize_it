import logging
from datetime import date
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Max, Min, Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override as translation_override
from django.views.decorators.http import require_http_methods
from django_q.tasks import async_task
from weasyprint import HTML

from accounts.models import Profile, get_profile
from trips.forms import TripForm
from trips.models import (
    Day,
    Event,
    MainTransfer,
    ShareLink,
    Stay,
    Trip,
    TripCollaboration,
)
from trips.utils import (
    geocode_trip_destination,
    get_flight_origin_icao,
    get_trip_for_editor_or_404,
    get_trip_for_owner_or_404,
    get_trip_stages,
    get_trips,
    group_days_by_destination,
    group_unpaired_events_by_stage,
    process_trip_image,
    search_unsplash_photos,
)

logger = logging.getLogger(__name__)


@login_not_required
def home(request):
    """Home page"""
    context = {}
    if request.user.is_authenticated:
        try:
            context = get_trips(request.user)
            context["show_guide"] = request.session.get("show_guide", False)
        except Profile.DoesNotExist:
            pass
    return TemplateResponse(request, "trips/index.html", context)


def toggle_guide(request):
    """Toggle the visibility of the quick guide in home page"""
    if request.method == "POST":
        current_state = request.session.get("show_guide", False)
        request.session["show_guide"] = not current_state
    return HttpResponse(status=204)


def trip_list(request):
    """List of all trips"""
    if request.htmx:
        template = "trips/trip-list.html#trip-list"
    else:
        template = "trips/trip-list.html"

    # Get user's sort preference
    sort_preference = get_profile(request.user).trip_sort_preference

    # Build base querysets
    active_trips = (
        Trip.objects.filter(author=request.user)
        .exclude(status=5)
        .prefetch_related("days")
    )
    archived_trips = Trip.objects.filter(
        author=request.user, status=5
    ).prefetch_related("days")
    shared_trips = (
        Trip.objects.filter(collaborators=request.user)
        .exclude(status=5)
        .prefetch_related("days")
    )

    # Apply sorting based on preference
    sort_map = {
        "date_asc": "start_date",
        "date_desc": "-start_date",
        "name_asc": "title",
        "name_desc": "-title",
    }

    order_by = sort_map.get(sort_preference, "start_date")
    active_trips = active_trips.order_by(order_by)
    archived_trips = archived_trips.order_by(order_by)
    shared_trips = shared_trips.order_by(order_by)

    context = {
        "active_trips": active_trips,
        "archived_trips": archived_trips,
        "shared_trips": shared_trips,
    }
    return TemplateResponse(request, template, context)


def trip_detail(request, pk):
    """
    Detail Page for the selected trip.
    Uses window functions to efficiently detect event overlaps within each day.
    """

    qs = Trip.objects.prefetch_related(
        Prefetch(
            "days__events",
            queryset=Event.objects.all().order_by("order", "pk"),
        ),
        Prefetch(
            "days__stay",
            queryset=Stay.objects.select_related("author"),
        ),
        Prefetch(
            "collaborations",
            queryset=TripCollaboration.objects.select_related("user__profile"),
        ),
    ).select_related("author")

    trip = get_object_or_404(
        qs.filter(Q(author=request.user) | Q(collaborators=request.user)).distinct(),
        pk=pk,
    )
    unpaired_events = trip.all_events.filter(day__isnull=True)
    stages = get_trip_stages(trip)
    grouped_unpaired_events = group_unpaired_events_by_stage(stages, unpaired_events)

    # Get unique stays ordered by first day date
    stays = (
        Stay.objects.filter(days__trip=trip)
        .annotate(first_day_date=Min("days__date"), last_day_date=Max("days__date"))
        .distinct()
        .order_by("first_day_date")
    )

    # Get main transfers
    arrival_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.DEPARTURE
    ).first()

    # Check user preference for default view
    profile = get_profile(request.user)
    show_map = profile.default_map_view == "map"

    days = trip.days.all()
    day_groups = group_days_by_destination(days)

    first_day = trip.days.order_by("number").first()
    last_day = trip.days.order_by("number").last()

    context = {
        "trip": trip,
        "stays": stays,
        "unpaired_events": unpaired_events,
        "grouped_unpaired_events": grouped_unpaired_events,
        "has_custom_stages": any(not s["is_main"] for s in stages),
        "arrival_transfer": arrival_transfer,
        "departure_transfer": departure_transfer,
        "both_transfers_exist": arrival_transfer is not None
        and departure_transfer is not None,
        "show_map": show_map,
        "today": date.today(),
        "arrival_origin_icao": get_flight_origin_icao(arrival_transfer),
        "departure_origin_icao": get_flight_origin_icao(departure_transfer),
        "day_groups": day_groups,
        "show_transfer_info": profile.show_transfer_info,
        "show_weather": profile.show_weather,
        "from_home_duration": first_day.transfer_duration_from_prev
        if first_day and not arrival_transfer
        else None,
        "from_home_distance": first_day.transfer_distance_from_prev
        if first_day and not arrival_transfer
        else None,
        "from_home_destination": (first_day.destination or trip.destination)
        if first_day and not arrival_transfer
        else None,
        "to_home_duration": last_day.transfer_to_home_duration
        if last_day and not departure_transfer
        else None,
        "to_home_distance": last_day.transfer_to_home_distance
        if last_day and not departure_transfer
        else None,
        "to_home_destination": (last_day.destination or trip.destination)
        if last_day and not departure_transfer
        else None,
    }
    if request.htmx:
        template = "trips/trip-detail.html#days"
    else:
        template = "trips/trip-detail.html"
    return TemplateResponse(request, template, context)


def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST, request.FILES)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.author = request.user

            # Process uploaded image if present (synchronous, takes priority)
            if request.FILES.get("image"):  # pragma: no cover
                processed_image = process_trip_image(request.FILES["image"])
                if processed_image:
                    trip.image = processed_image
                    trip.image_metadata = {"source": "upload"}

            # Schedule Unsplash download in background (only when no direct upload)
            selected_photo_id = form.cleaned_data.get("selected_photo_id")
            if selected_photo_id and not request.FILES.get("image"):
                trip.image = None
                trip.image_metadata = {"source": "unsplash", "pending": True}

            trip.save()

            if selected_photo_id and not request.FILES.get("image"):
                photos = search_unsplash_photos(trip.destination, per_page=10)
                if photos:
                    photo_data = next(
                        (p for p in photos if p["id"] == selected_photo_id), None
                    )
                    if photo_data:
                        async_task(
                            "trips.tasks.download_trip_unsplash_photo",
                            trip.pk,
                            photo_data,
                        )
            dest_lat = form.cleaned_data.get("destination_latitude")
            dest_lon = form.cleaned_data.get("destination_longitude")
            if dest_lat is not None and dest_lon is not None:
                Day.objects.filter(trip=trip).filter(
                    Q(destination="") | Q(destination=trip.destination)
                ).update(destination_latitude=dest_lat, destination_longitude=dest_lon)
            else:
                geocode_trip_destination(trip)
            messages.add_message(
                request,
                messages.SUCCESS,
                _("<strong>%(title)s</strong> added successfully")
                % {"title": trip.title},
            )
            if request.GET.get("next") == "list":
                return HttpResponse(
                    status=204, headers={"HX-Redirect": reverse("trips:trip-list")}
                )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm()
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-create.html", context)


@require_http_methods(["DELETE"])
def trip_delete(request, pk):
    trip = get_trip_for_owner_or_404(pk, request.user)
    trip.delete()
    messages.add_message(
        request,
        messages.ERROR,
        _("<strong>%(title)s</strong> deleted successfully") % {"title": trip.title},
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


def trip_update(request, pk):
    trip = get_trip_for_editor_or_404(pk, request.user)
    if request.method == "POST":
        form = TripForm(request.POST, request.FILES, instance=trip)
        if form.is_valid():
            trip = form.save(commit=False)

            # Process uploaded image if present (synchronous, takes priority)
            if request.FILES.get("image"):  # pragma: no cover
                processed_image = process_trip_image(request.FILES["image"])
                if processed_image:
                    trip.image = processed_image
                    trip.image_metadata = {"source": "upload"}

            # Schedule Unsplash download in background (only when no direct upload)
            selected_photo_id = form.cleaned_data.get("selected_photo_id")
            if selected_photo_id and not request.FILES.get("image"):
                trip.image = None
                trip.image_metadata = {"source": "unsplash", "pending": True}

            trip.save()

            if selected_photo_id and not request.FILES.get("image"):
                photos = search_unsplash_photos(trip.destination, per_page=10)
                if photos:
                    photo_data = next(
                        (p for p in photos if p["id"] == selected_photo_id), None
                    )
                    if photo_data:
                        async_task(
                            "trips.tasks.download_trip_unsplash_photo",
                            trip.pk,
                            photo_data,
                        )
            dest_lat = form.cleaned_data.get("destination_latitude")
            dest_lon = form.cleaned_data.get("destination_longitude")
            if dest_lat is not None and dest_lon is not None:
                Day.objects.filter(trip=trip).filter(
                    Q(destination="") | Q(destination=trip.destination)
                ).update(destination_latitude=dest_lat, destination_longitude=dest_lon)
            else:
                geocode_trip_destination(trip)
            messages.add_message(
                request,
                messages.SUCCESS,
                _("<strong>%(title)s</strong> updated successfully")
                % {"title": trip.title},
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
        context = {"form": form, "is_update": True}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm(instance=trip)
    context = {"form": form, "is_update": True}
    return TemplateResponse(request, "trips/trip-create.html", context)


def trip_archive(request, pk):
    trip = get_trip_for_owner_or_404(pk, request.user)
    trip.status = 5
    trip.save()

    # Reset fav_trip if this trip was the favourite
    profile = get_profile(request.user)
    if profile.fav_trip == trip:
        profile.fav_trip = None
        profile.save()

    messages.add_message(
        request,
        messages.SUCCESS,
        _("<strong>%(title)s</strong> archived successfully") % {"title": trip.title},
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


def trip_unarchive(request, pk):
    trip = get_trip_for_owner_or_404(pk, request.user)
    trip.status = Trip.Status.NOT_STARTED
    trip.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("<strong>%(title)s</strong> unarchived successfully") % {"title": trip.title},
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved", "HX-Refresh": "true"},
    )


def validate_dates(request):
    """
    Validate the start and end dates of a trip.
    If the start date is after the end date or before today, return an HTML snippet with an error message.
    """
    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    errors = []

    # Parse dates if present
    try:
        if start_date:
            start_date_obj = date.fromisoformat(start_date)
        else:
            start_date_obj = None
        if end_date:
            end_date_obj = date.fromisoformat(end_date)
        else:
            end_date_obj = None
    except ValueError:
        # If parsing fails, skip further checks
        return HttpResponse("")

    # Check if start_date is before today
    trip_id = request.GET.get("trip_id")
    if not trip_id and start_date_obj and start_date_obj < date.today():
        errors.append(_("Start date must be after today."))

    # Check if start_date is after end_date
    if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
        errors.append(_("Start date cannot be after end date."))

    if errors:
        html = "".join(
            [
                format_html(
                    """
                <div class="alert alert-error alert-soft flex items-center gap-2 mt-2" x-data>
                    <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M12 8v4m0 4h.01M21 12A9 9 0 1 1 3 12a9 9 0 0 1 18 0Z" />
                    </svg>
                    <span>{}</span>
                </div>
                """,
                    error,
                )
                for error in errors
            ]
        )
        return HttpResponse(html)
    return HttpResponse("")


def search_trip_images(request):
    """HTMX endpoint for searching Unsplash images using destination"""
    if request.method == "POST":
        query = request.POST.get("destination", "").strip()
        trip_id = request.POST.get("trip_id")

        if not query:
            return TemplateResponse(
                request,
                "trips/includes/image-search-results.html",
                {"error": _("Please enter a destination first")},
            )

        # Search Unsplash
        photos = search_unsplash_photos(query, per_page=3)

        if photos is None:
            return TemplateResponse(
                request,
                "trips/includes/image-search-results.html",
                {"error": _("Unsplash API error. Please try again later.")},
            )

        if not photos:
            return TemplateResponse(
                request,
                "trips/includes/image-search-results.html",
                {"error": _("No images found for '{query}'").format(query=query)},
            )

        return TemplateResponse(
            request,
            "trips/includes/image-search-results.html",
            {"photos": photos, "trip_id": trip_id, "query": query},
        )

    return HttpResponse(status=405)


@require_http_methods(["GET"])
def trip_image_status(request, pk):
    """HTMX polling endpoint: returns spinner fragment while Unsplash task is pending, image when ready."""
    from trips.utils import accessible_trips_qs

    trip = get_object_or_404(Trip, pk=pk)
    if not accessible_trips_qs(request.user).filter(pk=trip.pk).exists():
        raise Http404
    return TemplateResponse(
        request,
        "trips/includes/trip-image-status-fragment.html",
        {"trip": trip},
    )


@login_not_required
def shared_trip_detail(request, token):
    """Public read-only view for a shared trip. No login required."""
    link = get_object_or_404(ShareLink.objects.select_related("trip"), id=token)

    if not link.is_valid:
        if link.expires_at:
            return TemplateResponse(request, "trips/link-expired.html", status=410)
        return TemplateResponse(request, "trips/link-revoked.html", status=410)

    days = link.trip.days.prefetch_related(
        Prefetch(
            "events",
            queryset=Event.objects.all().order_by("order", "pk"),
        ),
        Prefetch(
            "stay",
            queryset=Stay.objects.select_related("author"),
        ),
    ).order_by("date")

    context = {
        "trip": link.trip,
        "days": days,
        "is_shared_view": True,
        "permission_level": link.permission_level,
    }
    return TemplateResponse(request, "trips/shared-trip-detail.html", context)


def build_pdf_export_context(trip):
    """Build the template context for the trip PDF export."""
    days = list(
        trip.days.prefetch_related(
            Prefetch("events", queryset=Event.objects.order_by("order", "pk")),
            "stay",
        )
        .select_related("trip")
        .order_by("number")
    )
    seen_stays: set[int] = set()
    events_count = 0
    for day in days:
        if day.stay_id and day.stay_id not in seen_stays:
            day.show_stay = True
            seen_stays.add(day.stay_id)
        else:
            day.show_stay = False
        events_count += len(day.events.all())

    arrival_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.DEPARTURE
    ).first()
    main_transfers = [mt for mt in (arrival_transfer, departure_transfer) if mt]
    links = list(trip.links.all())

    summary = {
        "days": len(days),
        "events": events_count,
        "stays": len(seen_stays),
        "links": len(links),
    }

    trip_image_url = None
    if trip.image:
        try:
            trip_image_url = f"file://{trip.image.path}"
        except NotImplementedError, ValueError:
            trip_image_url = trip.image.url

    return {
        "trip": trip,
        "trip_image_url": trip_image_url,
        "days": days,
        "arrival_transfer": arrival_transfer,
        "departure_transfer": departure_transfer,
        "main_transfers": main_transfers,
        "links": links,
        "summary": summary,
    }


def export_trip_pdf(request, pk):
    """Export a trip itinerary as a PDF file."""
    trip = get_object_or_404(
        Trip.objects.filter(
            Q(author=request.user) | Q(collaborators=request.user)
        ).distinct(),
        pk=pk,
    )

    context = build_pdf_export_context(trip)
    language = get_profile(request.user).language or "en"
    with translation_override(language):
        html_string = render_to_string("trips/trip-pdf.html", context, request=request)
    pdf_file = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(
        pdf_file
    )
    pdf_file.seek(0)

    filename = f"trip-{trip.pk}-itinerary.pdf"
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
