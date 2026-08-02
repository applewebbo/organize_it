"""Trip utilities, split by responsibility.

Import paths remain backward compatible: `from trips.utils import X` keeps
working for every helper thanks to the re-exports below.
"""

from trips.utils.events import build_categorized_event, get_event_instance
from trips.utils.geocoding import (
    convert_google_opening_hours,
    fetch_route,
    generate_cache_key,
    geocode_city,
    geocode_location,
    geocode_trip_destination,
    rate_limit_check,
    select_best_result,
)
from trips.utils.images import (
    download_unsplash_photo,
    process_trip_image,
    search_unsplash_photos,
)
from trips.utils.maps import create_day_map, create_trip_map
from trips.utils.queries import (
    accessible_trips_qs,
    editable_trips_qs,
    get_trip_for_editor_or_404,
    get_trip_for_owner_or_404,
    get_trip_or_404,
    get_trips,
)
from trips.utils.stages import (
    apply_stage,
    get_trip_stages,
    group_days_by_destination,
    group_unpaired_events_by_stage,
)
from trips.utils.stay22 import build_stay22_url
from trips.utils.transport import (
    get_airport_by_iata,
    get_flight_origin_icao,
    get_station_by_id,
    load_airports,
    load_train_stations,
    search_airports,
    search_train_stations,
)

__all__ = [
    "accessible_trips_qs",
    "build_categorized_event",
    "build_stay22_url",
    "convert_google_opening_hours",
    "create_day_map",
    "create_trip_map",
    "download_unsplash_photo",
    "editable_trips_qs",
    "fetch_route",
    "generate_cache_key",
    "geocode_city",
    "geocode_location",
    "geocode_trip_destination",
    "get_airport_by_iata",
    "get_event_instance",
    "get_flight_origin_icao",
    "get_station_by_id",
    "get_trip_for_editor_or_404",
    "get_trip_for_owner_or_404",
    "get_trip_or_404",
    "apply_stage",
    "get_trip_stages",
    "get_trips",
    "group_days_by_destination",
    "group_unpaired_events_by_stage",
    "load_airports",
    "load_train_stations",
    "process_trip_image",
    "rate_limit_check",
    "search_airports",
    "search_train_stations",
    "search_unsplash_photos",
    "select_best_result",
]
