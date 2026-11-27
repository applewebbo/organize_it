from django.db.models import Max, Min

from trips.models import MainTransfer

DAY_COLORS = [
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#06b6d4",
    "#8b5cf6",
    "#ec4899",
    "#14b8a6",
    "#f43f5e",
    "#6366f1",
]
STAY_ICON_COLOR = "#6b7280"


def build_trip_map_data(days_with_events, unassigned_events):
    """Build JSON-serializable map data for all trip days, stays, and unassigned events."""
    all_points = []
    stays = []
    days = []
    unassigned = []
    seen_stay_pks = set()

    for idx, day_data in enumerate(days_with_events, start=1):
        day = day_data["day"]
        color = DAY_COLORS[(idx - 1) % len(DAY_COLORS)]

        stay = day_data["stay"]
        if stay and stay.pk not in seen_stay_pks and stay.latitude and stay.longitude:
            seen_stay_pks.add(stay.pk)
            all_points.append((stay.latitude, stay.longitude))
            stays.append(
                {
                    "lat": stay.latitude,
                    "lng": stay.longitude,
                    "name": stay.name,
                }
            )

        day_events = []
        for ev in day_data["events"]:
            if not (ev.latitude and ev.longitude):
                continue
            all_points.append((ev.latitude, ev.longitude))
            day_events.append(
                {
                    "lat": ev.latitude,
                    "lng": ev.longitude,
                    "name": ev.name,
                    "kind": "meal" if ev.category == 3 else "experience",
                }
            )

        days.append(
            {
                "label": f"Giorno {idx} — {day.date.strftime('%d %b')}",
                "color": color,
                "events": day_events,
            }
        )

    for ev in unassigned_events:
        if not (ev.latitude and ev.longitude):
            continue
        all_points.append((ev.latitude, ev.longitude))
        unassigned.append(
            {
                "lat": ev.latitude,
                "lng": ev.longitude,
                "name": ev.name,
                "kind": "meal" if ev.category == 3 else "experience",
            }
        )

    if not all_points:
        return None

    return {
        "mode": "trip",
        "stays": stays,
        "days": days,
        "unassigned": unassigned,
        "bounds": [
            [min(p[0] for p in all_points), min(p[1] for p in all_points)],
            [max(p[0] for p in all_points), max(p[1] for p in all_points)],
        ],
    }


def _expand_bounds(bounds, lat, lng):
    bounds["min_lat"] = min(bounds["min_lat"] or lat, lat)
    bounds["max_lat"] = max(bounds["max_lat"] or lat, lat)
    bounds["min_lon"] = min(bounds["min_lon"] or lng, lng)
    bounds["max_lon"] = max(bounds["max_lon"] or lng, lng)


def build_day_map_data(events_with_location, stay, next_day_stay, day=None):
    """
    Build JSON-serializable map data for a given day with events, stays, and main transfers.

    Args:
        events_with_location: QuerySet of events with coordinates
        stay: Stay object for the current day
        next_day_stay: Stay object for the next day (if different)
        day: Optional Day object (for main transfer integration)
    """
    if not events_with_location and (not stay or not stay.latitude):
        return None

    bounds = events_with_location.aggregate(
        min_lat=Min("latitude"),
        max_lat=Max("latitude"),
        min_lon=Min("longitude"),
        max_lon=Max("longitude"),
    )

    markers = []

    for event in events_with_location:
        markers.append(
            {
                "lat": event.latitude,
                "lng": event.longitude,
                "name": event.name,
                "kind": "experience" if event.category == 2 else "meal",
            }
        )

    if stay and stay.latitude and stay.longitude:
        _expand_bounds(bounds, stay.latitude, stay.longitude)
        markers.append(
            {
                "lat": stay.latitude,
                "lng": stay.longitude,
                "name": stay.name,
                "kind": "stay",
            }
        )

    if (
        next_day_stay
        and next_day_stay != stay
        and next_day_stay.latitude
        and next_day_stay.longitude
    ):
        _expand_bounds(bounds, next_day_stay.latitude, next_day_stay.longitude)
        markers.append(
            {
                "lat": next_day_stay.latitude,
                "lng": next_day_stay.longitude,
                "name": next_day_stay.name,
                "tooltip": f"Next day: {next_day_stay.name}",
                "kind": "stay",
            }
        )

    if day:
        trip = day.trip
        total_days = trip.days.count()
        transfer_icon_map = {
            MainTransfer.Type.PLANE: "airplane-takeoff",
            MainTransfer.Type.TRAIN: "train",
            MainTransfer.Type.CAR: "car",
        }

        if day.number == 1:
            arrival = trip.main_transfers.filter(
                direction=MainTransfer.Direction.ARRIVAL
            ).first()
            if (
                arrival
                and arrival.destination_latitude
                and arrival.destination_longitude
            ):
                _expand_bounds(
                    bounds,
                    arrival.destination_latitude,
                    arrival.destination_longitude,
                )
                markers.append(
                    {
                        "lat": arrival.destination_latitude,
                        "lng": arrival.destination_longitude,
                        "name": f"Arrival: {arrival.destination_name}",
                        "kind": "transfer",
                        "icon": transfer_icon_map.get(arrival.type, "person-walking"),
                    }
                )

        if day.number == total_days:
            departure = trip.main_transfers.filter(
                direction=MainTransfer.Direction.DEPARTURE
            ).first()
            if departure and departure.origin_latitude and departure.origin_longitude:
                _expand_bounds(
                    bounds, departure.origin_latitude, departure.origin_longitude
                )
                markers.append(
                    {
                        "lat": departure.origin_latitude,
                        "lng": departure.origin_longitude,
                        "name": f"Departure: {departure.origin_name}",
                        "kind": "transfer",
                        "icon": transfer_icon_map.get(departure.type, "person-walking"),
                    }
                )

    bias = 0.005
    return {
        "mode": "day",
        "markers": markers,
        "bounds": [
            [bounds["min_lat"] - bias, bounds["min_lon"] - bias],
            [bounds["max_lat"] + bias, bounds["max_lon"] + bias],
        ],
    }
