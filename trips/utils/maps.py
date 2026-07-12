import folium
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
STAY_ICON_COLOR = "gray"


def create_trip_map(days_with_events, unassigned_events):
    """
    Create a unified Folium map for all trip days.
    Each day is a FeatureGroup with a distinct color; LayerControl allows toggling.
    Stays use a neutral gray icon. Returns the HTML string (iframe srcdoc).
    """
    all_points = []

    # Collect any point to check if map is worth creating
    for day_data in days_with_events:
        stay = day_data["stay"]
        if stay and stay.latitude:
            all_points.append((stay.latitude, stay.longitude))
        for ev in day_data["events"]:
            if ev.latitude and ev.longitude:
                all_points.append((ev.latitude, ev.longitude))
    for ev in unassigned_events:
        if ev.latitude and ev.longitude:
            all_points.append((ev.latitude, ev.longitude))

    if not all_points:
        return None

    center = [
        sum(p[0] for p in all_points) / len(all_points),
        sum(p[1] for p in all_points) / len(all_points),
    ]

    m = folium.Map(
        location=center, zoom_start=12, tiles=None, width="100%", height="500px"
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        name="Mappa",
        control=False,
    ).add_to(m)

    seen_stay_pks = set()
    fg_stays = folium.FeatureGroup(
        name='<span style="display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:-1px;background:#6b7280;margin-right:5px"></span>Soggiorni'
    )

    for idx, day_data in enumerate(days_with_events, start=1):
        day = day_data["day"]
        color = DAY_COLORS[(idx - 1) % len(DAY_COLORS)]
        fg = folium.FeatureGroup(
            name=f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;vertical-align:-1px;background:{color};margin-right:5px"></span>Giorno {idx} — {day.date.strftime("%d %b")}'
        )

        stay = day_data["stay"]
        if stay and stay.pk not in seen_stay_pks and stay.latitude and stay.longitude:
            seen_stay_pks.add(stay.pk)
            folium.Marker(
                [stay.latitude, stay.longitude],
                popup=stay.name,
                tooltip=stay.name,
                icon=folium.DivIcon(
                    html='<div style="background:#6b7280;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.8);box-shadow:0 2px 5px rgba(0,0,0,0.35)"><i class="fa fa-bed" style="color:white;font-size:13px"></i></div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    popup_anchor=(0, -15),
                ),
            ).add_to(fg_stays)

        for ev in day_data["events"]:
            if not (ev.latitude and ev.longitude):
                continue
            icon_name = "cutlery" if ev.category == 3 else "map-marker"
            folium.Marker(
                [ev.latitude, ev.longitude],
                popup=ev.name,
                tooltip=ev.name,
                icon=folium.DivIcon(
                    html=f'<div style="background:{color};width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.8);box-shadow:0 2px 5px rgba(0,0,0,0.35)"><i class="fa fa-{icon_name}" style="color:white;font-size:13px"></i></div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    popup_anchor=(0, -15),
                ),
            ).add_to(fg)

        fg.add_to(m)

    if seen_stay_pks:
        fg_stays.add_to(m)

    fg_unassigned = folium.FeatureGroup(name="Senza giorno")
    has_unassigned = False
    for ev in unassigned_events:
        if not (ev.latitude and ev.longitude):
            continue
        folium.Marker(
            [ev.latitude, ev.longitude],
            popup=ev.name,
            tooltip=ev.name,
            icon=folium.DivIcon(
                html='<div style="background:#9ca3af;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid rgba(255,255,255,0.8);box-shadow:0 2px 5px rgba(0,0,0,0.35)"><i class="fa fa-map-marker" style="color:white;font-size:13px"></i></div>',
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                popup_anchor=(0, -15),
            ),
        ).add_to(fg_unassigned)
        has_unassigned = True
    if has_unassigned:
        fg_unassigned.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds(
        [
            [min(p[0] for p in all_points), min(p[1] for p in all_points)],
            [max(p[0] for p in all_points), max(p[1] for p in all_points)],
        ],
        padding=[30, 30],
    )

    return m._repr_html_()


def create_day_map(events_with_location, stay, next_day_stay, day=None):
    """
    Create a map for a given day with events, stay, and next day stay.

    Args:
        events_with_location: QuerySet of events with coordinates
        stay: Stay object for the current day
        next_day_stay: Stay object for the next day (if different)
        day: Optional Day object (for main transfer integration)
    """
    # Check if there's anything to show on the map
    if not events_with_location and (not stay or not stay.latitude):
        return None

    # Aggregate event locations
    bounds = events_with_location.aggregate(
        min_lat=Min("latitude"),
        max_lat=Max("latitude"),
        min_lon=Min("longitude"),
        max_lon=Max("longitude"),
    )

    # Include stay location in bounds calculation
    if stay and stay.latitude and stay.longitude:
        bounds["min_lat"] = min(bounds["min_lat"] or stay.latitude, stay.latitude)
        bounds["max_lat"] = max(bounds["max_lat"] or stay.latitude, stay.latitude)
        bounds["min_lon"] = min(bounds["min_lon"] or stay.longitude, stay.longitude)
        bounds["max_lon"] = max(bounds["max_lon"] or stay.longitude, stay.longitude)

    # Include next day's stay in bounds calculation if different
    if next_day_stay and next_day_stay != stay and next_day_stay.latitude:
        bounds["min_lat"] = min(
            bounds["min_lat"] or next_day_stay.latitude, next_day_stay.latitude
        )
        bounds["max_lat"] = max(
            bounds["max_lat"] or next_day_stay.latitude, next_day_stay.latitude
        )
        bounds["min_lon"] = min(
            bounds["min_lon"] or next_day_stay.longitude, next_day_stay.longitude
        )
        bounds["max_lon"] = max(
            bounds["max_lon"] or next_day_stay.longitude, next_day_stay.longitude
        )

    # Include main transfers if this is the first or last day
    main_transfer_markers = []
    if day:
        trip = day.trip
        total_days = trip.days.count()

        # First day: include ARRIVAL transfer destination
        if day.number == 1:
            arrival = trip.main_transfers.filter(
                direction=MainTransfer.Direction.ARRIVAL
            ).first()

            if (
                arrival
                and arrival.destination_latitude
                and arrival.destination_longitude
            ):
                # Include in bounds
                bounds["min_lat"] = min(
                    bounds["min_lat"] or arrival.destination_latitude,
                    arrival.destination_latitude,
                )
                bounds["max_lat"] = max(
                    bounds["max_lat"] or arrival.destination_latitude,
                    arrival.destination_latitude,
                )
                bounds["min_lon"] = min(
                    bounds["min_lon"] or arrival.destination_longitude,
                    arrival.destination_longitude,
                )
                bounds["max_lon"] = max(
                    bounds["max_lon"] or arrival.destination_longitude,
                    arrival.destination_longitude,
                )

                # Store for marker creation later
                main_transfer_markers.append(
                    {
                        "lat": arrival.destination_latitude,
                        "lon": arrival.destination_longitude,
                        "name": arrival.destination_name,
                        "type": "arrival",
                        "transport_type": arrival.type,
                    }
                )

        # Last day: include DEPARTURE transfer origin
        if day.number == total_days:
            departure = trip.main_transfers.filter(
                direction=MainTransfer.Direction.DEPARTURE
            ).first()

            if departure and departure.origin_latitude and departure.origin_longitude:
                # Include in bounds
                bounds["min_lat"] = min(
                    bounds["min_lat"] or departure.origin_latitude,
                    departure.origin_latitude,
                )
                bounds["max_lat"] = max(
                    bounds["max_lat"] or departure.origin_latitude,
                    departure.origin_latitude,
                )
                bounds["min_lon"] = min(
                    bounds["min_lon"] or departure.origin_longitude,
                    departure.origin_longitude,
                )
                bounds["max_lon"] = max(
                    bounds["max_lon"] or departure.origin_longitude,
                    departure.origin_longitude,
                )

                # Store for marker creation later
                main_transfer_markers.append(
                    {
                        "lat": departure.origin_latitude,
                        "lon": departure.origin_longitude,
                        "name": departure.origin_name,
                        "type": "departure",
                        "transport_type": departure.type,
                    }
                )

    # Create a map
    m = folium.Map(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains="abcd",
        width="100%",
        height="100%",
    )
    # Add a bias
    bias = 0.005
    fit_bounds_payload = [
        [bounds["min_lat"] - bias, bounds["min_lon"] - bias],
        [bounds["max_lat"] + bias, bounds["max_lon"] + bias],
    ]
    m.fit_bounds(fit_bounds_payload)

    # Add specific icons
    experience_icon = folium.Icon(prefix="fa", color="green", icon="images")
    meal_icon = folium.Icon(prefix="fa", color="orange", icon="utensils")
    stay_icon = folium.Icon(prefix="fa", color="blue", icon="bed")

    # Add markers for each event
    for event in events_with_location:
        icon = experience_icon if event.category == 2 else meal_icon
        folium.Marker(
            [event.latitude, event.longitude],
            popup=event.name,
            tooltip=event.name,
            icon=icon,
        ).add_to(m)

    # Add marker for the stay
    if stay and stay.latitude and stay.longitude:
        folium.Marker(
            [stay.latitude, stay.longitude],
            popup=stay.name,
            tooltip=stay.name,
            icon=stay_icon,
        ).add_to(m)

    # Add marker for the next day's stay if it's different
    if (
        next_day_stay
        and next_day_stay != stay
        and next_day_stay.latitude
        and next_day_stay.longitude
    ):
        folium.Marker(
            [next_day_stay.latitude, next_day_stay.longitude],
            popup=next_day_stay.name,
            tooltip=f"Next day: {next_day_stay.name}",
            icon=stay_icon,
        ).add_to(m)

    # Add markers for main transfers (arrival/departure)
    for marker_data in main_transfer_markers:
        label = "Arrival" if marker_data["type"] == "arrival" else "Departure"

        # Choose icon based on transport type
        transport_type = marker_data.get("transport_type")
        if transport_type == MainTransfer.Type.PLANE:
            icon_name = "plane"
        elif transport_type == MainTransfer.Type.TRAIN:
            icon_name = "train"
        elif transport_type == MainTransfer.Type.CAR:
            icon_name = "car"
        else:  # OTHER
            icon_name = "person-walking"

        icon = folium.Icon(prefix="fa", color="red", icon=icon_name)

        folium.Marker(
            [marker_data["lat"], marker_data["lon"]],
            popup=f"{label}: {marker_data['name']}",
            tooltip=f"{label}: {marker_data['name']}",
            icon=icon,
        ).add_to(m)

    return m._repr_html_()
