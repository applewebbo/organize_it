---
# organize_it-x893
title: Add weather forecasts to trip days
status: completed
type: feature
priority: normal
created_at: 2026-03-21T12:35:06Z
updated_at: 2026-03-21T19:35:02Z
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
- [x] Include weather data in shared_trip_detail context

### Phase 5 — Tests (TDD)
- [x] Save Open-Meteo fixture JSON in tests/fixtures/ (replaced with dynamic conftest fixture)
- [x] Test parse_weather_response with fixture
- [x] Test get_coordinates_for_day (all fallbacks)
- [x] Test WMO_CODE_MAP completeness
- [x] Test fetch_weather_for_active_trips filters by status
- [x] Test weather widget shown/hidden based on trip status
- [x] Test shared view includes weather

## Summary of Changes

Implemented full weather forecast feature using Open-Meteo API (issue #237):

- New fields on `Day`: `weather_data` (JSONField) + `weather_fetched_at`
- `trips/weather.py`: `fetch_raw_weather`, `parse_weather_response`, `get_coordinates_for_day`, `fetch_weather_for_day`, `fetch_weather_for_trip`, WMO_CODE_MAP (28 codes → Phosphor icons)
- Background task `fetch_weather_for_active_trips` scheduled every 6h via migration
- Template tags: `weather_widget`, `weather_summary`, `trip_day_one_weather`
- Templates: weather widget in day cards, summary banner in trip header, badge in trip list
- Weather shown in shared (magic link) view
- pytest-httpx for HTTP boundary testing (no code mocking)
- 710 tests, 100% coverage
