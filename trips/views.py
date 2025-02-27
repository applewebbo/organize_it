from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from accounts.models import Profile

from .forms import (
    ExperienceForm,
    MealForm,
    StayForm,
    TransportForm,
    TripDateUpdateForm,
    TripForm,
)
from .models import Day, Trip

# def calculate_bounds(locations):
#     # TODO: add check for a single location
#     # Check if the list is not empty
#     if not locations:
#         return None

#     sw = list(min((point["latitude"], point["longitude"]) for point in locations))
#     ne = list(max((point["latitude"], point["longitude"]) for point in locations))

#     return [sw, ne]


# def calculate_days_and_locations(trip):
#     days = (
#         Day.objects.filter(trip=trip)
#         .exclude(places__isnull=True)
#         .prefetch_related("places")
#     )
#     locations = list(
#         Place.objects.filter(trip=trip).values("name", "latitude", "longitude")
#     )

#     return days, locations


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
    qs = Trip.objects.prefetch_related("days", "days__events")
    trip = get_object_or_404(qs, pk=pk)
    # days, locations = calculate_days_and_locations(pk)
    # not_assigned_locations = Place.na_objects.filter(trip=pk)
    # map_bounds = calculate_bounds(locations)

    context = {
        "trip": trip,
        # "locations": locations,
        # "not_assigned_locations": not_assigned_locations,
        # "map_bounds": map_bounds,
    }
    return TemplateResponse(request, "trips/trip-detail.html", context)


# @login_required
# def map(request, pk, day=None):
#     """Get map details as a separate view to serve with htmx"""
#     qs = Trip.objects.prefetch_related("places", "days")
#     trip = get_object_or_404(qs, pk=pk)
#     days = Day.objects.filter(trip=pk, places__isnull=False).distinct()
#     if day:
#         locations = list(
#             Place.objects.filter(trip=pk, day=day).values(
#                 "name", "latitude", "longitude"
#             )
#         )

#     else:
#         locations = list(
#             Place.objects.filter(trip=pk).values("name", "latitude", "longitude")
#         )
#     map_bounds = calculate_bounds(locations)

#     context = {
#         "trip": trip,
#         "locations": locations,
#         "map_bounds": map_bounds,
#         "selected_day": day,
#         "days": days,
#     }

#     return TemplateResponse(request, "trips/includes/map.html", context)


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


def add_transport(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    form = TransportForm(request.POST or None)
    if form.is_valid():
        transport = form.save(commit=False)
        transport.day = day
        transport.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Transport added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form}
    return TemplateResponse(request, "trips/transport-create.html", context)


def add_experience(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    form = ExperienceForm(request.POST or None)
    if form.is_valid():
        experience = form.save(commit=False)
        experience.day = day
        experience.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Experience added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form}
    return TemplateResponse(request, "trips/experience-create.html", context)


def add_meal(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    form = MealForm(request.POST or None)
    if form.is_valid():
        meal = form.save(commit=False)
        meal.day = day
        meal.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Meal added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form}
    return TemplateResponse(request, "trips/meal-create.html", context)


def add_stay(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    trip = day.trip
    form = StayForm(trip, request.POST or None)
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
    context = {"form": form}
    return TemplateResponse(request, "trips/stay-create.html", context)
