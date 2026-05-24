import json
import logging
from datetime import date
from urllib.parse import quote as urlquote

import geocoder
import requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from accounts.models import get_profile
from trips.forms import (
    CarMainTransferForm,
    FlightMainTransferForm,
    MainTransferConnectionEditForm,
    MainTransferConnectionForm,
    OtherMainTransferForm,
    StayTransferCreateForm,
    StayTransferEditForm,
    TrainMainTransferForm,
)
from trips.models import (
    Day,
    Event,
    MainTransfer,
    MainTransferConnection,
    Stay,
    StayTransfer,
)
from trips.utils import (
    accessible_trips_qs,
    editable_trips_qs,
    fetch_route,
    get_airport_by_iata,
    get_flight_origin_icao,
    get_trip_for_editor_or_404,
    get_trip_or_404,
    search_airports,
    search_train_stations,
)

logger = logging.getLogger(__name__)


def create_stay_transfer(request, from_day_id):
    """
    Create a StayTransfer between stays of consecutive days.
    The from_stay and to_stay are auto-populated from the days.
    The button to create a transfer only appears on the last day of a stay
    (where next_day has a different stay), so next_day is the correct to_day.
    """
    from_day = get_object_or_404(
        Day, pk=from_day_id, trip__in=editable_trips_qs(request.user)
    )

    # Get the next day - the button only appears when next_day exists and has different stay
    to_day = from_day.next_day
    if not to_day:
        messages.add_message(
            request,
            messages.ERROR,
            _("No next day found for this stay"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    # Check if both days have stays
    if not from_day.stay or not to_day.stay:
        messages.add_message(
            request,
            messages.ERROR,
            _("Both days must have stays to create a transfer"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    from_stay = from_day.stay
    to_stay = to_day.stay

    # Check if stays are different (can't transfer from/to same stay)
    if from_stay == to_stay:
        messages.add_message(
            request,
            messages.ERROR,
            _("Cannot create transfer between the same stay"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    form = StayTransferCreateForm(
        request.POST or None,
        from_stay=from_stay,
        to_stay=to_stay,
    )

    if form.is_valid():
        stay_transfer = form.save(commit=False)
        # from_stay and to_event are already set by the form's __init__
        stay_transfer.from_day = from_day
        stay_transfer.to_day = to_day
        stay_transfer.trip = from_day.trip
        stay_transfer.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay transfer created successfully"),
        )
        # Trigger both days to refresh
        triggers = {f"dayModified{from_day.pk}": {}, f"dayModified{to_day.pk}": {}}
        return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(triggers)})

    context = {
        "form": form,
        "from_day": from_day,
        "to_day": to_day,
        "from_stay": from_stay,
        "to_stay": to_stay,
    }
    return TemplateResponse(request, "trips/stay-transfer-create.html", context)


def edit_stay_transfer(request, pk):
    """Edit an existing StayTransfer"""
    qs = StayTransfer.objects.select_related(
        "from_stay", "to_stay", "from_day__trip__author", "to_day", "trip"
    )
    stay_transfer = get_object_or_404(
        qs, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    form = StayTransferEditForm(request.POST or None, instance=stay_transfer)

    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Stay transfer updated successfully"),
        )
        # Trigger both days to refresh
        triggers = {
            f"dayModified{stay_transfer.from_day.pk}": {},
            f"dayModified{stay_transfer.to_day.pk}": {},
        }
        return HttpResponse(status=204, headers={"HX-Trigger": json.dumps(triggers)})

    context = {"form": form, "stay_transfer": stay_transfer}
    return TemplateResponse(request, "trips/stay-transfer-edit.html", context)


def delete_stay_transfer(request, pk):
    """Delete a StayTransfer"""
    qs = StayTransfer.objects.select_related("from_day__trip__author", "to_day")
    stay_transfer = get_object_or_404(
        qs, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    from_day_id = stay_transfer.from_day.pk
    to_day_id = stay_transfer.to_day.pk
    stay_transfer.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Stay transfer deleted successfully"),
    )
    # Trigger refresh of both days to update their UI
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": f"dayModified{from_day_id}, dayModified{to_day_id}"},
    )


def edit_main_transfer(request, pk):
    """Edit existing main transfer - opens modal with specific form"""
    transfer = get_object_or_404(
        MainTransfer, pk=pk, trip__in=editable_trips_qs(request.user)
    )
    trip = transfer.trip

    # Form class mapper
    FORM_MAP = {
        MainTransfer.Type.PLANE: FlightMainTransferForm,
        MainTransfer.Type.TRAIN: TrainMainTransferForm,
        MainTransfer.Type.CAR: CarMainTransferForm,
        MainTransfer.Type.OTHER: OtherMainTransferForm,
    }

    form_class = FORM_MAP[transfer.type]

    if request.method == "POST":
        # Handle form submission
        form = form_class(
            request.POST,
            instance=transfer,
            trip=trip,
            autocomplete=True,
            home_address="",
        )
        if form.is_valid():
            form.save()
            message = str(_("Main transfer updated successfully"))
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps(
                        {
                            "tripModified": {},
                            "hide-modal": {},
                            "showMessage": {
                                "type": "success",
                                "message": message,
                            },
                        }
                    )
                },
            )
        # If form is invalid, fall through to return form with errors
    else:
        # GET request - show form with existing data
        form = form_class(
            instance=transfer, trip=trip, autocomplete=True, home_address=""
        )

    direction_str = (
        "arrival"
        if transfer.direction == MainTransfer.Direction.ARRIVAL
        else "departure"
    )

    context = {
        "trip": trip,
        "form": form,
        "transport_type": transfer.type,
        "direction": direction_str,
        "is_edit": True,
        "is_edit_modal": True,
    }

    return TemplateResponse(request, "trips/edit-main-transfer-modal.html", context)


def delete_main_transfer(request, pk):
    """Delete main transfer"""
    transfer = get_object_or_404(
        MainTransfer, pk=pk, trip__in=editable_trips_qs(request.user)
    )

    transfer.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Main transfer deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


def train_status_redirect(request, pk):
    """Redirect to viaggiatreno for train status (specific train or station board)."""
    transfer = get_object_or_404(
        MainTransfer,
        pk=pk,
        trip__in=accessible_trips_qs(request.user),
        type=MainTransfer.Type.TRAIN,
    )

    base = (
        "http://www.viaggiatreno.it/infomobilitamobile/pages/cercaTreno/cercaTreno.jsp"
    )
    train_number = transfer.train_number

    if train_number:
        # Specific train: look up origin station id and datapartenza
        try:
            resp = requests.get(
                f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
                f"/cercaNumeroTrenoTrenoAutocomplete/{train_number}",
                timeout=5,
            )
            if resp.ok and resp.text:
                # Format: "2822 - MILANO CENTRALE - 23/03/26|2822-S01700-1774220400000"
                token = resp.text.strip().split("|")[-1]  # "2822-S01700-1774220400000"
                parts = token.split("-")
                if len(parts) == 3:
                    _, origine, datapartenza = parts
                    return redirect(
                        f"{base}?treno={train_number}&origine={origine}&datapartenza={datapartenza}"
                    )
        except Exception as exc:
            logger.warning(
                "Viaggiatreno train lookup failed for %s: %s", train_number, exc
            )

    # Fallback: station departure board
    station_name = transfer.origin_name
    first_word = station_name.split()[0] if station_name else ""
    try:
        resp = requests.get(
            f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
            f"/cercaStazione/{first_word}",
            timeout=5,
        )
        if resp.ok:
            stations = resp.json()
            # Find best match by normalized name
            match = next(
                (s for s in stations if s["nomeLungo"].upper() == station_name.upper()),
                stations[0] if stations else None,
            )
            if match:
                nome = urlquote(match["nomeLungo"])
                return redirect(f"{base}?cod={match['id']}&nome={nome}")
    except Exception as exc:
        logger.warning(
            "Viaggiatreno station lookup failed for %s: %s", station_name, exc
        )

    # Last resort: viaggiatreno homepage
    return redirect("http://www.viaggiatreno.it/infomobilitamobile/pages/home/home.jsp")


def flight_status_redirect(request, pk):
    """Redirect to FlightAware for flight status (specific flight or airport board)."""
    transfer = get_object_or_404(
        MainTransfer,
        pk=pk,
        trip__in=accessible_trips_qs(request.user),
        type=MainTransfer.Type.PLANE,
    )

    flight_number = transfer.flight_number
    if flight_number:
        return redirect(f"https://it.flightaware.com/live/flight/{flight_number}")

    # Fallback: airport departure/arrival board via ICAO code
    iata_code = transfer.origin_code
    if iata_code:
        airport = get_airport_by_iata(iata_code)
        if airport and airport.get("icao_code"):
            return redirect(
                f"https://it.flightaware.com/live/airport/{airport['icao_code']}"
            )

    return redirect("https://it.flightaware.com")


def main_transfers_section(request, trip_id):
    """HTMX endpoint: returns main transfers section for trip detail page"""
    trip = get_trip_or_404(trip_id, request.user)

    # Get main transfers
    arrival_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.ARRIVAL
    ).first()
    departure_transfer = MainTransfer.objects.filter(
        trip=trip, direction=MainTransfer.Direction.DEPARTURE
    ).first()

    context = {
        "trip": trip,
        "arrival_transfer": arrival_transfer,
        "departure_transfer": departure_transfer,
        "both_transfers_exist": arrival_transfer is not None
        and departure_transfer is not None,
        "today": date.today(),
        "arrival_origin_icao": get_flight_origin_icao(arrival_transfer),
        "departure_origin_icao": get_flight_origin_icao(departure_transfer),
    }

    return TemplateResponse(request, "trips/includes/main-transfers.html", context)


def main_transfer_connection_modal(request, main_transfer_pk):
    """Show modal with event/stay options for creating a main transfer connection"""
    main_transfer = get_object_or_404(
        MainTransfer, pk=main_transfer_pk, trip__in=accessible_trips_qs(request.user)
    )

    # Check if connection already exists
    existing_connection = None
    try:
        existing_connection = main_transfer.connection
    except MainTransferConnection.DoesNotExist:
        pass

    trip = main_transfer.trip

    # Determine available options based on direction
    if main_transfer.direction == MainTransfer.Direction.ARRIVAL:
        # For ARRIVAL: first day's stay and first event
        first_day = trip.days.first()
        available_stay = first_day.stay if first_day else None
        available_event = (
            first_day.events.order_by("order", "pk").first() if first_day else None
        )
    else:
        # For DEPARTURE: last day's stay and last event
        last_day = trip.days.last()
        available_stay = last_day.stay if last_day else None
        available_event = (
            last_day.events.order_by("order", "pk").last() if last_day else None
        )

    context = {
        "main_transfer": main_transfer,
        "existing_connection": existing_connection,
        "available_stay": available_stay,
        "available_event": available_event,
    }
    return TemplateResponse(
        request, "trips/main-transfer-connection-modal.html", context
    )


def create_main_transfer_connection(request, main_transfer_pk, destination_type):
    """Create a MainTransferConnection to event or stay"""
    main_transfer = get_object_or_404(
        MainTransfer, pk=main_transfer_pk, trip__in=editable_trips_qs(request.user)
    )

    # Check if connection already exists
    if hasattr(main_transfer, "connection"):
        messages.add_message(
            request,
            messages.ERROR,
            _("A connection already exists for this main transfer"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    trip = main_transfer.trip

    # Get the destination based on type and direction
    if destination_type not in ["event", "stay"]:
        messages.add_message(
            request,
            messages.ERROR,
            _("Invalid destination type"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    # Determine the destination object
    if main_transfer.direction == MainTransfer.Direction.ARRIVAL:
        first_day = trip.days.first()
        if not first_day:
            messages.add_message(
                request,
                messages.ERROR,
                _("No days available in this trip"),
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})

        if destination_type == "stay":
            destination = first_day.stay
        else:
            destination = first_day.events.order_by("order", "pk").first()
    else:
        # DEPARTURE
        last_day = trip.days.last()
        if not last_day:
            messages.add_message(
                request,
                messages.ERROR,
                _("No days available in this trip"),
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})

        if destination_type == "stay":
            destination = last_day.stay
        else:
            destination = last_day.events.order_by("order", "pk").last()

    if not destination:
        messages.add_message(
            request,
            messages.ERROR,
            _(f"No {destination_type} available for this connection"),
        )
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})

    form = MainTransferConnectionForm(
        request.POST or None,
        main_transfer=main_transfer,
        destination=destination,
        destination_type=destination_type,
    )

    if form.is_valid():
        connection = form.save(commit=False)
        connection.main_transfer = main_transfer
        if destination_type == "event":
            connection.event = destination
        else:
            connection.stay = destination
        connection.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Connection created successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    context = {
        "form": form,
        "main_transfer": main_transfer,
        "destination": destination,
        "destination_type": destination_type,
    }
    return TemplateResponse(
        request, "trips/main-transfer-connection-create.html", context
    )


def edit_main_transfer_connection(request, pk):
    """Edit an existing MainTransferConnection"""
    qs = MainTransferConnection.objects.select_related(
        "main_transfer__trip__author", "event", "stay"
    )
    connection = get_object_or_404(
        qs, pk=pk, main_transfer__trip__in=editable_trips_qs(request.user)
    )

    form = MainTransferConnectionEditForm(request.POST or None, instance=connection)

    if form.is_valid():
        form.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Connection updated successfully"),
        )
        return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})

    context = {"form": form, "connection": connection}
    return TemplateResponse(
        request, "trips/main-transfer-connection-edit.html", context
    )


def delete_main_transfer_connection(request, pk):
    """Delete a MainTransferConnection"""
    qs = MainTransferConnection.objects.select_related("main_transfer__trip__author")
    connection = get_object_or_404(
        qs, pk=pk, main_transfer__trip__in=editable_trips_qs(request.user)
    )
    connection.delete()
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Connection deleted successfully"),
    )
    return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})


def transfer_info(request, day_pk):
    """HTMX polling endpoint: return transfer-info fragment for the first day of an arriving stage."""
    if not get_profile(request.user).show_transfer_info:
        return HttpResponse(status=204)
    day = get_object_or_404(
        Day.objects.select_related("trip", "stay").prefetch_related("events"),
        pk=day_pk,
        trip__in=accessible_trips_qs(request.user),
    )
    prev_day = Day.objects.filter(trip=day.trip, number=day.number - 1).first()
    from_dest = prev_day.destination if prev_day else None
    next_destination = day.destination or day.trip.destination
    return TemplateResponse(
        request,
        "trips/includes/transfer-info.html",
        {
            "day_pk": day_pk,
            "from_dest": from_dest,
            "next_destination": next_destination,
            "transfer_duration": day.transfer_duration_from_prev,
            "transfer_distance": day.transfer_distance_from_prev,
        },
    )


def get_trip_addresses(request):
    """Get addresses from existing events and stays in a trip for transport origin/destination selection."""
    if request.method == "POST":
        trip_id = request.POST.get("trip_id", "").strip()
        field_type = request.POST.get(
            "field_type", ""
        ).strip()  # 'origin' or 'destination'

        if trip_id:
            trip = get_trip_or_404(trip_id, request.user)
            stays_addresses = []
            events_addresses = []

            # Get addresses from stays (always return all stays)
            stays = (
                Stay.objects.filter(days__trip=trip)
                .exclude(address="")
                .exclude(city="")
                .distinct()
                .order_by("name")
            )
            for stay in stays:
                stays_addresses.append(
                    {
                        "name": stay.name,
                        "address": stay.address,
                        "city": stay.city,
                        "type": "stay",
                    }
                )

            # Get addresses from events
            events = (
                Event.objects.filter(trip=trip)
                .exclude(address="")
                .exclude(city="")
                .order_by("name")
            )

            # Track unique events to avoid duplicates
            seen_events = set()
            for event in events:
                # Create a unique key based on name, address, and city
                event_key = (
                    event.name.lower().strip(),
                    event.address.lower().strip(),
                    event.city.lower().strip(),
                )

                if event_key not in seen_events:
                    seen_events.add(event_key)
                    events_addresses.append(
                        {
                            "name": event.name,
                            "address": event.address,
                            "city": event.city,
                            "type": "event",
                        }
                    )

            if stays_addresses or events_addresses:
                return TemplateResponse(
                    request,
                    "trips/includes/trip-address-results.html",
                    {
                        "stays": stays_addresses,
                        "events": events_addresses,
                        "found": True,
                        "field_type": field_type,
                    },
                )

        return TemplateResponse(
            request, "trips/includes/trip-address-results.html", {"found": False}
        )

    return TemplateResponse(
        request, "trips/includes/trip-address-results.html", {"found": False}
    )


def search_airports_view(request):
    """
    HTMX endpoint for airport autocomplete.
    Searches airports by name, city, or IATA code from CSV.
    """
    if request.method == "POST":
        query = request.POST.get("airport_query", "").strip()
        field_type = request.GET.get(
            "field_type", request.POST.get("field_type", "origin")
        )

        if query and len(query) >= 2:
            results = search_airports(query, limit=10)
            if results:
                return TemplateResponse(
                    request,
                    "trips/includes/airport-results.html",
                    {
                        "airports": results,
                        "found": True,
                        "field_type": field_type,
                    },
                )

        return TemplateResponse(
            request,
            "trips/includes/airport-results.html",
            {"found": False, "field_type": field_type},
        )

    return TemplateResponse(
        request,
        "trips/includes/airport-results.html",
        {"found": False, "field_type": "origin"},
    )


def search_stations(request):
    """
    HTMX endpoint for train station autocomplete.
    Searches stations by name or country from CSV.
    """
    if request.method == "POST":
        query = request.POST.get("station_query", "").strip()
        field_type = request.GET.get(
            "field_type", request.POST.get("field_type", "origin")
        )

        if query and len(query) >= 2:
            results = search_train_stations(query, limit=10)
            if results:
                return TemplateResponse(
                    request,
                    "trips/includes/station-results.html",
                    {
                        "stations": results,
                        "found": True,
                        "field_type": field_type,
                    },
                )

        return TemplateResponse(
            request,
            "trips/includes/station-results.html",
            {"found": False, "field_type": field_type},
        )

    return TemplateResponse(
        request,
        "trips/includes/station-results.html",
        {"found": False, "field_type": "origin"},
    )


def arrival_transfer_modal(request, trip_id):
    """Entry point for arrival transfer modal (2-step wizard)."""
    trip = get_trip_or_404(trip_id, request.user)

    # Default transport type to PLANE
    transport_type = MainTransfer.Type.PLANE

    context = {
        "trip": trip,
        "transport_type": transport_type,
    }

    return TemplateResponse(request, "trips/arrival-transfer-modal.html", context)


def departure_transfer_modal(request, trip_id):
    """Entry point for departure transfer modal (2-step wizard)."""
    trip = get_trip_or_404(trip_id, request.user)

    # Default transport type to PLANE
    transport_type = MainTransfer.Type.PLANE

    context = {
        "trip": trip,
        "transport_type": transport_type,
    }

    return TemplateResponse(request, "trips/departure-transfer-modal.html", context)


def main_transfer_step(request, trip_id):
    """HTMX endpoint to load specific step of multi-step modal."""
    trip = get_trip_or_404(trip_id, request.user)
    step = request.GET.get("step", "type")

    # Map string to transport type
    TYPE_MAP = {
        "plane": MainTransfer.Type.PLANE,
        "train": MainTransfer.Type.TRAIN,
        "car": MainTransfer.Type.CAR,
        "other": MainTransfer.Type.OTHER,
    }
    transport_type_param = request.GET.get("transport_type", "plane")
    transport_type = TYPE_MAP.get(transport_type_param, MainTransfer.Type.PLANE)

    # Form mapper
    FORM_MAP = {
        MainTransfer.Type.PLANE: FlightMainTransferForm,
        MainTransfer.Type.TRAIN: TrainMainTransferForm,
        MainTransfer.Type.CAR: CarMainTransferForm,
        MainTransfer.Type.OTHER: OtherMainTransferForm,
    }

    # Get direction from query param (for new separate modals)
    direction_param = request.GET.get("direction", "")

    if step == "type":
        # Determine if this is for departure based on direction parameter
        for_departure = direction_param == "departure"

        context = {
            "trip": trip,
            "transport_type": transport_type,
            "for_departure": for_departure,
            "direction": direction_param,
        }
        return TemplateResponse(
            request, "trips/partials/main-transfer-type.html", context
        )

    elif step in ["arrival", "departure"]:
        # Use direction from query param if present, otherwise infer from step
        if direction_param:
            direction = (
                MainTransfer.Direction.ARRIVAL
                if direction_param == "arrival"
                else MainTransfer.Direction.DEPARTURE
            )
        else:
            direction = (
                MainTransfer.Direction.ARRIVAL
                if step == "arrival"
                else MainTransfer.Direction.DEPARTURE
            )

        instance = MainTransfer.objects.filter(trip=trip, direction=direction).first()
        form_class = FORM_MAP[transport_type]

        # Build home_address and quick_fill_locations for car forms only
        home_address = ""
        quick_fill_locations = []
        if transport_type == MainTransfer.Type.CAR:
            home_address = get_profile(request.user).home_address

            if direction == MainTransfer.Direction.ARRIVAL:
                ref_day = (
                    trip.days.prefetch_related("events", "stay")
                    .order_by("date")
                    .first()
                )
            else:
                ref_day = (
                    trip.days.prefetch_related("events", "stay")
                    .order_by("-date")
                    .first()
                )

            if ref_day:
                if hasattr(ref_day, "stay") and ref_day.stay and ref_day.stay.address:
                    quick_fill_locations.append(
                        {
                            "label": ref_day.stay.name,
                            "address": ref_day.stay.address,
                            "type": "stay",
                        }
                    )
                for event in ref_day.events.order_by("order", "pk"):
                    if event.address:
                        event_type = (
                            "meal"
                            if event.category == Event.Category.MEAL
                            else "experience"
                        )
                        quick_fill_locations.append(
                            {
                                "label": event.name,
                                "address": event.address,
                                "type": event_type,
                            }
                        )

            if not quick_fill_locations:
                quick_fill_locations = [
                    {
                        "label": trip.destination,
                        "address": trip.destination,
                        "type": "destination",
                    }
                ]

        form = form_class(
            instance=instance,
            trip=trip,
            autocomplete=True,
            home_address=home_address,
            initial={"direction": direction},
        )

        # Check if form was pre-filled from arrival
        prefilled = getattr(form, "prefilled_from_arrival", False)

        context = {
            "trip": trip,
            "form": form,
            "step": step,
            "transport_type": transport_type,
            "direction": "arrival" if step == "arrival" else "departure",
            "prefilled_from_arrival": prefilled,
            "quick_fill_locations": quick_fill_locations,
        }

        template_map = {
            MainTransfer.Type.PLANE: "trips/partials/main-transfer-flight.html",
            MainTransfer.Type.TRAIN: "trips/partials/main-transfer-train.html",
            MainTransfer.Type.CAR: "trips/partials/main-transfer-car.html",
            MainTransfer.Type.OTHER: "trips/partials/main-transfer-other.html",
        }

        return TemplateResponse(request, template_map[transport_type], context)

    return HttpResponse("Invalid step", status=400)


def save_main_transfer(request, trip_id):
    """Save main transfer (arrival or departure)."""
    trip = get_trip_for_editor_or_404(trip_id, request.user)

    if request.method != "POST":
        return HttpResponse(status=405)

    # Get transport_type and direction from query params
    TYPE_MAP = {
        "plane": MainTransfer.Type.PLANE,
        "train": MainTransfer.Type.TRAIN,
        "car": MainTransfer.Type.CAR,
        "other": MainTransfer.Type.OTHER,
    }
    transport_type_param = request.GET.get("transport_type", "plane")
    transport_type = TYPE_MAP.get(transport_type_param, MainTransfer.Type.PLANE)

    direction_param = request.GET.get("direction", "arrival")
    direction = (
        MainTransfer.Direction.ARRIVAL
        if direction_param == "arrival"
        else MainTransfer.Direction.DEPARTURE
    )

    FORM_MAP = {
        MainTransfer.Type.PLANE: FlightMainTransferForm,
        MainTransfer.Type.TRAIN: TrainMainTransferForm,
        MainTransfer.Type.CAR: CarMainTransferForm,
        MainTransfer.Type.OTHER: OtherMainTransferForm,
    }

    form_class = FORM_MAP[transport_type]
    instance = MainTransfer.objects.filter(trip=trip, direction=direction).first()
    form = form_class(
        request.POST, instance=instance, trip=trip, autocomplete=False, home_address=""
    )

    if form.is_valid():
        transfer = form.save(commit=False)
        transfer.trip = trip
        transfer.type = transport_type
        transfer.direction = direction
        if not instance:
            transfer.last_modified_by = request.user
        transfer.save()

        # Always close modal and refresh trip
        message = str(_("Transfer saved successfully!"))
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "tripModified": {},
                        "hide-modal": {},
                        "showMessage": {
                            "type": "success",
                            "message": message,
                        },
                    }
                )
            },
        )

    # Return form with errors
    context = {
        "trip": trip,
        "form": form,
        "transport_type": transport_type,
        "direction": direction_param,
    }

    template_map = {
        MainTransfer.Type.PLANE: "trips/partials/main-transfer-flight.html",
        MainTransfer.Type.TRAIN: "trips/partials/main-transfer-train.html",
        MainTransfer.Type.CAR: "trips/partials/main-transfer-car.html",
        MainTransfer.Type.OTHER: "trips/partials/main-transfer-other.html",
    }

    return TemplateResponse(request, template_map[transport_type], context)


def estimate_car_duration(request, trip_id):
    """Return estimated driving duration between two addresses for car transfer forms."""
    get_trip_for_editor_or_404(trip_id, request.user)

    origin = request.GET.get("origin_address", "").strip()
    destination = request.GET.get("destination_address", "").strip()

    duration_minutes = None
    distance_km = None

    if origin and destination:
        g1 = geocoder.mapbox(origin, access_token=settings.MAPBOX_ACCESS_TOKEN)
        g2 = geocoder.mapbox(destination, access_token=settings.MAPBOX_ACCESS_TOKEN)
        if g1.latlng and g2.latlng:
            lat1, lng1 = g1.latlng
            lat2, lng2 = g2.latlng
            result = fetch_route(lat1, lng1, lat2, lng2)
            if result:
                duration_minutes, distance_km = result

    hours = duration_minutes // 60 if duration_minutes else None
    mins = duration_minutes % 60 if duration_minutes else None
    context = {
        "duration_minutes": duration_minutes,
        "distance_km": distance_km,
        "hours": hours,
        "mins": mins,
    }
    return TemplateResponse(
        request, "trips/partials/car-duration-estimate.html", context
    )
