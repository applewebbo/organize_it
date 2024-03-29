from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Profile

from .forms import (
    LinkForm,
    NoteForm,
    PlaceAssignForm,
    PlaceForm,
    TripDateUpdateForm,
    TripForm,
)
from .models import Day, Link, Note, Place, Trip


def calculate_bounds(locations):
    # TODO: add check for a single location
    # Check if the list is not empty
    if not locations:
        return None

    sw = list(min((point["latitude"], point["longitude"]) for point in locations))
    ne = list(max((point["latitude"], point["longitude"]) for point in locations))

    return [sw, ne]


def calculate_days_and_locations(trip):
    days = (
        Day.objects.filter(trip=trip)
        .exclude(places__isnull=True)
        .prefetch_related("places")
    )
    locations = list(
        Place.objects.filter(trip=trip).values("name", "latitude", "longitude")
    )

    return days, locations


def get_trips(user):
    """Get the trips for the home page with favourite trip (if present) and others"""
    fav_trip = Profile.objects.get(user=user).fav_trip or None
    if fav_trip:
        other_trips = (
            Trip.objects.filter(author=user).exclude(pk=fav_trip.pk).order_by("status")
        )
    else:
        other_trips = Trip.objects.filter(author=user).order_by("status")
    context = {
        "other_trips": other_trips,
        "fav_trip": fav_trip,
    }
    return context


def home(request):
    """Home page"""
    context = {}
    if request.user.is_authenticated:
        if Profile.objects.filter(user=request.user).exists():
            context = get_trips(request.user)
    return TemplateResponse(request, "trips/index.html", context)


@login_required
def trip_list(request):
    """List of all trips"""
    if request.htmx:
        template = "trips/trip-list.html#trip-list"
    else:
        template = "trips/trip-list.html"
    active_trips = Trip.objects.filter(author=request.user).exclude(status=5)
    archived_trips = Trip.objects.filter(author=request.user, status=5)
    context = {
        "active_trips": active_trips,
        "archived_trips": archived_trips,
    }
    return TemplateResponse(request, template, context)


@login_required
def trip_detail(request, pk):
    """Detail Page for the selected trip"""
    qs = Trip.objects.prefetch_related("links", "places", "notes")
    trip = get_object_or_404(qs, pk=pk)
    days, locations = calculate_days_and_locations(pk)
    not_assigned_locations = Place.na_objects.filter(trip=pk)
    map_bounds = calculate_bounds(locations)

    context = {
        "trip": trip,
        "days": days,
        "locations": locations,
        "not_assigned_locations": not_assigned_locations,
        "map_bounds": map_bounds,
    }
    return TemplateResponse(request, "trips/trip-detail.html", context)


@login_required
def map(request, pk, day=None):
    """Get map details as a separate view to serve with htmx"""
    qs = Trip.objects.prefetch_related("places", "days")
    trip = get_object_or_404(qs, pk=pk)
    days = Day.objects.filter(trip=pk, places__isnull=False).distinct()
    if day:
        locations = list(
            Place.objects.filter(trip=pk, day=day).values(
                "name", "latitude", "longitude"
            )
        )

    else:
        locations = list(
            Place.objects.filter(trip=pk).values("name", "latitude", "longitude")
        )
    map_bounds = calculate_bounds(locations)

    context = {
        "trip": trip,
        "locations": locations,
        "map_bounds": map_bounds,
        "selected_day": day,
        "days": days,
    }

    return TemplateResponse(request, "trips/includes/map.html", context)


@login_required
def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.author = request.user
            trip.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{trip.title}</strong> added successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm()
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-create.html", context)


@login_required
@require_http_methods(["DELETE"])
def trip_delete(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    trip.delete()
    messages.add_message(
        request,
        messages.ERROR,
        f"<strong>{trip.title}</strong> deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


@login_required
def trip_update(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    if request.method == "POST":
        form = TripForm(request.POST or None, instance=trip)
        if form.is_valid():
            trip = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                f"<strong>{trip.title}</strong> updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        form = TripForm(request.POST, instance=trip)
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-create.html", context)

    form = TripForm(instance=trip)
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-create.html", context)


def trip_archive(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    trip.status = 5
    trip.save()
    messages.add_message(
        request,
        messages.SUCCESS,
        f"<strong>{trip.title}</strong> archived successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "tripSaved"},
    )


def trip_dates_update(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)

    form = TripDateUpdateForm(request.POST or None, instance=trip)
    if form.is_valid():
        trip = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Dates updated successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/trip-dates-update.html", context)


@login_required
def trip_add_link(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)

    form = LinkForm(request.POST or None)
    if form.is_valid():
        link = form.save(commit=False)
        link.author = request.user
        link.save()
        trip.links.add(link)
        trip.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Link added successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "linkSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/link-create.html", context)


@login_required
@require_http_methods(["DELETE"])
def link_delete(request, pk):
    link = get_object_or_404(Link, pk=pk, author=request.user)
    link.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Link deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "linkSaved"},
    )


@login_required
def link_update(request, pk):
    link = get_object_or_404(Link, pk=pk, author=request.user)

    form = LinkForm(request.POST or None, instance=link)
    if form.is_valid():
        link = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Link updated successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "linkSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/link-create.html", context)


@login_required
def link_list(request, pk):
    links = Link.objects.filter(trips=pk)
    trip = get_object_or_404(Trip, pk=pk)
    context = {"links": links, "trip": trip}
    return TemplateResponse(request, "trips/trip-detail.html#link-list", context)


@login_required
def trip_add_place(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    form = PlaceForm(request.POST or None, parent=trip)
    if form.is_valid():
        place = form.save(commit=False)
        place.trip = trip
        place.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            f"<strong>{place.name}</strong> added successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "placeSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/place-create.html", context)


@login_required
def place_list(request, pk):
    qs = Trip.objects.prefetch_related("links", "places", "notes")
    trip = get_object_or_404(qs, pk=pk)
    days, locations = calculate_days_and_locations(pk)
    not_assigned_locations = Place.na_objects.filter(trip=pk)
    map_bounds = calculate_bounds(locations)

    context = {
        "trip": trip,
        "days": days,
        "locations": locations,
        "not_assigned_locations": not_assigned_locations,
        "map_bounds": map_bounds,
    }
    return TemplateResponse(request, "trips/trip-detail.html#place-list", context)


@login_required
@require_http_methods(["DELETE"])
def place_delete(request, pk):
    place = get_object_or_404(Place, pk=pk, trip__author=request.user)
    place.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Place deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "placeSaved"},
    )


@login_required
def place_update(request, pk):
    place = get_object_or_404(Place, pk=pk, trip__author=request.user)

    form = PlaceForm(request.POST or None, instance=place)
    if form.is_valid():
        place = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Place updated successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "placeSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/place-create.html", context)


@login_required
def place_assign(request, pk):
    place = get_object_or_404(Place, pk=pk, trip__author=request.user)
    if request.method == "POST":
        form = PlaceAssignForm(request.POST, instance=place)
        if form.is_valid():
            place = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Place assigned successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "placeSaved"})
        form = PlaceAssignForm(request.POST, instance=place)
        context = {"form": form, "place": place}
        return TemplateResponse(request, "trips/place-create.html", context)

    form = PlaceAssignForm(instance=place)
    context = {"form": form, "place": place}
    return TemplateResponse(request, "trips/place-assign.html", context)


@login_required
def trip_add_note(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)

    form = NoteForm(trip, request.POST or None)
    if form.is_valid():
        note = form.save(commit=False)
        note.trip = trip
        note.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Note added successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "noteSaved"})

    context = {"form": form}
    return TemplateResponse(request, "trips/note-create.html", context)


@login_required
def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk, trip__author=request.user)

    form = NoteForm(note.trip, request.POST or None, instance=note)
    if form.is_valid():
        note = form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            "Note updated successfully",
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "noteSaved"})

    context = {"form": form, "note": note}
    return TemplateResponse(request, "trips/note-update.html", context)


@login_required
def note_list(request, pk):
    notes = Note.objects.filter(trip=pk)
    trip = get_object_or_404(Trip, pk=pk)
    context = {"notes": notes, "trip": trip}
    return TemplateResponse(request, "trips/trip-detail.html#note-list", context)


@login_required
@require_http_methods(["DELETE"])
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, trip__author=request.user)
    note.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        "Note deleted successfully",
    )
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "noteSaved"},
    )


@login_required
@require_POST
def note_check_or_uncheck(request, pk):
    note = get_object_or_404(Note, pk=pk, trip__author=request.user)
    note.checked = not note.checked
    note.save()
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "noteSaved"},
    )
