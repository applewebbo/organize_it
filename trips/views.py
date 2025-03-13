from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
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
from .models import Day, Event, Stay, Trip

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
    qs = Trip.objects.prefetch_related(
        "days__events",
        "days__stay",
    ).select_related("author")
    trip = get_object_or_404(qs, pk=pk)

    context = {
        "trip": trip,
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
def add_stay(request, day_id):
    day = get_object_or_404(Day, pk=day_id, trip__author=request.user)
    trip = day.trip
    form = StayForm(trip, request.POST or None, initial={"apply_to_days": [day_id]})
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay added successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form}
    return TemplateResponse(request, "trips/stay-create.html", context)


@login_required
def stay_detail(request, pk):
    stay = get_object_or_404(Stay, pk=pk)
    days = stay.days.order_by("date")
    last_day = days.last()
    first_stay_day = days.first()

    # Find the day before the first stay day in the trip's days
    first_day = (
        Day.objects.filter(
            trip=first_stay_day.trip, date=first_stay_day.date - timedelta(days=1)
        ).first()
        or first_stay_day
    )

    context = {
        "stay": stay,
        "first_day": first_day,
        "last_day": last_day,
    }
    return TemplateResponse(request, "trips/stay-detail.html", context)


@login_required
def stay_modify(request, pk):
    qs = Stay.objects.prefetch_related("days")
    stay = get_object_or_404(qs, pk=pk)
    trip = stay.days.first().trip
    form = StayForm(trip, request.POST or None, instance=stay)
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form, "stay": stay}
    return TemplateResponse(request, "trips/stay-modify.html", context)


@login_required
def stay_delete(request, pk):
    stay = get_object_or_404(Stay, pk=pk)
    trip = stay.days.first().trip
    other_stays = Stay.objects.filter(days__trip=trip).exclude(pk=pk).distinct()

    if request.method == "POST":
        if other_stays.count() == 1:
            # Automatically reassign to the only remaining stay
            new_stay = other_stays.first()
            stay.days.update(stay=new_stay)
        else:
            new_stay_id = request.POST.get("new_stay")
            if new_stay_id:
                new_stay = Stay.objects.get(pk=new_stay_id)
                stay.days.update(stay=new_stay)

        stay.delete()
        messages.add_message(
            request,
            messages.ERROR,
            _("Stay deleted successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    context = {
        "stay": stay,
        "other_stays": other_stays,
        "show_dropdown": len(other_stays) > 1,
    }
    return TemplateResponse(request, "trips/stay-delete.html", context)


@login_required
@require_http_methods(["DELETE"])
def event_delete(request, pk):
    qs = Event.objects.select_related("day__trip__author")
    event = get_object_or_404(qs, pk=pk, day__trip__author=request.user)
    event.delete()
    messages.add_message(
        request,
        messages.ERROR,
        _("Event deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
def event_modify(request, pk):
    qs = Event.objects.select_related("day__trip")
    event = get_object_or_404(qs, pk=pk, day__trip__author=request.user)

    # Select form class based on event category
    event_form = {
        1: TransportForm,  # Transport
        2: ExperienceForm,  # Experience
        3: MealForm,  # Meal
    }.get(event.category)

    if not event_form:
        raise Http404("Invalid event category")

    form = event_form(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Event updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    context = {"form": form, "event": event}
    return TemplateResponse(request, "trips/event-modify.html", context)
