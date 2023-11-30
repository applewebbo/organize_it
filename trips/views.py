from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Profile

from .forms import LinkForm, NoteForm, PlaceForm, TripDateUpdateForm, TripForm
from .models import Link, Note, Place, Trip


def calculate_bounds(locations):
    # Check if the list is not empty
    if not locations:
        return None

    sw = list(min((point["latitude"], point["longitude"]) for point in locations))
    ne = list(max((point["latitude"], point["longitude"]) for point in locations))

    return [sw, ne]


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
    qs = Trip.objects.prefetch_related("links", "places", "notes")
    trip = get_object_or_404(qs, pk=pk)

    locations = list(Place.objects.filter(trip=pk).values("latitude", "longitude"))
    map_bounds = calculate_bounds(locations)

    context = {
        "trip": trip,
        "locations": locations,
        "map_bounds": map_bounds,
    }
    if request.htmx:
        # redraw the map section only
        template = "trips/trip-detail.html#trip-detail"
    else:
        template = "trips/trip-detail.html"

    return TemplateResponse(request, template, context)


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
        form = TripForm(request.POST)
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
        messages.SUCCESS,
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
        form = TripForm(request.POST, instance=trip)
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
    if request.method == "POST":
        form = TripDateUpdateForm(request.POST, instance=trip)
        if form.is_valid():
            trip = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Dates updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "tripSaved"})
        form = TripDateUpdateForm(request.POST, instance=trip)
        context = {"form": form}
        return TemplateResponse(request, "trips/trip-dates-update.html", context)

    form = TripDateUpdateForm(instance=trip)
    context = {"form": form}
    return TemplateResponse(request, "trips/trip-dates-update.html", context)


@login_required
def trip_add_link(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    if request.method == "POST":
        form = LinkForm(request.POST)
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

    form = LinkForm()
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

    if request.method == "POST":
        form = LinkForm(request.POST, instance=link)
        if form.is_valid():
            link = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Link updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "linkSaved"})

    form = LinkForm(instance=link)
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
    trip = get_object_or_404(Trip, pk=pk, author=request.user)
    if request.method == "POST":
        form = PlaceForm(request.POST)
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
    form = PlaceForm()
    context = {"form": form}
    return TemplateResponse(request, "trips/place-create.html", context)


@login_required
def place_list(request, pk):
    places = Place.objects.filter(trip=pk)
    trip = get_object_or_404(Trip, pk=pk)
    locations = list(places.values("latitude", "longitude"))
    map_bounds = calculate_bounds(locations)
    context = {
        "places": places,
        "trip": trip,
        "locations": locations,
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

    if request.method == "POST":
        form = PlaceForm(request.POST, instance=place)
        if form.is_valid():
            place = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Place updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "placeSaved"})

    form = PlaceForm(instance=place)
    context = {"form": form}
    return TemplateResponse(request, "trips/place-create.html", context)


@login_required
def trip_add_note(request, pk):
    trip = get_object_or_404(Trip, pk=pk, author=request.user)

    if request.method == "POST":
        form = NoteForm(trip, request.POST)
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

        form = NoteForm(trip, request.POST)
        context = {"form": form}
        return TemplateResponse(request, "trips/note-create.html", context)

    form = NoteForm(trip)
    context = {"form": form}
    return TemplateResponse(request, "trips/note-create.html", context)


@login_required
def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk, trip__author=request.user)
    if request.method == "POST":
        form = NoteForm(note.trip, request.POST, instance=note)
        if form.is_valid():
            note = form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Note updated successfully",
            )
            return HttpResponse(status=204, headers={"HX-Trigger": "noteSaved"})

        form = NoteForm(note.trip, instance=note)
        context = {"form": form}
        return TemplateResponse(request, "trips/note-create.html", context)

    form = NoteForm(note.trip, instance=note)
    context = {"form": form}
    return TemplateResponse(request, "trips/note-create.html", context)


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
