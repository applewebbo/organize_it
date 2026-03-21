---
# organize_it-x893
title: Add weather forecasts to trip days
status: in-progress
type: feature
priority: normal
created_at: 2026-03-21T12:35:06Z
updated_at: 2026-03-21T13:51:09Z
---

Add weather forecast data to trip days for IMPENDING and IN_PROGRESS trips.

**Related to:** #237

## Checklist

### Phase 1 — Model & Data Layer
- [x] Add weather_data JSONField + weather_fetched_at to Day model
- [x] Create migration
- [x] Create trips/weather.py with fetch_raw_weather, parse_weather_response, get_coordinates_for_day
- [x] WMO_CODE_MAP: codici WMO → icona Phosphor + label

### Phase 2 — Background Tasks
- [x] Add fetch_weather_for_trip(trip) task
- [x] Add fetch_weather_for_active_trips() scheduled task
- [x] Update settings.py schedule (every 6h)

### Phase 3 — Template Tag & Templates
- [x] Add weather_widget template tag in trip_tags.py
- [x] Create trips/weather-widget.html fragment
- [x] Add weather summary banner to trip-detail.html header
- [x] Add weather badge to trip-list.html

### Phase 4 — Shared View
- [ ] Include weather data in shared_trip_detail context

### Phase 5 — Tests (TDD)
- [ ] Save Open-Meteo fixture JSON in tests/fixtures/
- [ ] Test parse_weather_response with fixture
- [ ] Test get_coordinates_for_day (all fallbacks)
- [ ] Test WMO_CODE_MAP completeness
- [ ] Test fetch_weather_for_active_trips filters by status
- [ ] Test weather widget shown/hidden based on trip status
- [ ] Test shared view includes weather
