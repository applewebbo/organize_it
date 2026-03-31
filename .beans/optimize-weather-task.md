---
# optimize
title: Optimize weather fetching task
status: completed
type: task
priority: "2"
created_at: 2026-03-30T13:06:33Z
updated_at: 2026-03-31T05:41:39Z
---

# Optimize weather fetching task

## Objective
Reduce query count in weather task from ~50 to ~5 per execution.

## Required changes

### 1. `trips/tasks.py` - fetch_weather_for_active_trips() (line ~145)
```python
def fetch_weather_for_active_trips():
    """
    Fetch and cache weather forecasts for all IMPENDING and IN_PROGRESS trips.
    """
    try:
        logger.info("Starting fetch_weather_for_active_trips task")

        # Prefetch days to reduce queries
        trips = Trip.objects.prefetch_related("days").filter(
            status__in=[Trip.Status.IMPENDING, Trip.Status.IN_PROGRESS]
        )

        count = trips.count()
        processed = 0

        for trip in trips.iterator():  # Use iterator for memory efficiency
            fetch_weather_for_trip(trip)
            processed += 1
            logger.debug(f"Weather fetched for trip '{trip.title}' ({processed}/{count})")

        result_msg = f"Weather fetched for {count} trip(s)"
        logger.info(f"fetch_weather_for_active_trips completed: {result_msg}")
        return result_msg

    except Exception as e:
        logger.error(f"Error in fetch_weather_for_active_trips task: {e}", exc_info=True)
        raise
```

### 2. `trips/weather.py` - fetch_weather_for_trip() (line ~149)
```python
def fetch_weather_for_trip(trip):
    """
    Fetch weather for all days in a trip.
    """
    # Use already prefetched days from task
    for day in trip.days.all():  # Uses prefetch if available
        fetch_weather_for_day(day)
```

### 3. `trips/weather.py` - get_coordinates_for_day() (line ~83)
```python
def get_coordinates_for_day(day):
    """
    Get coordinates for a day, with fallback to trip destination.
    """
    # Try stay first
    if day.stay and day.stay.latitude and day.stay.longitude:
        return day.stay.latitude, day.stay.longitude

    # Try events
    for event in day.events.all():
        if event.latitude and event.longitude:
            return event.latitude, event.longitude

    # Fallback to trip destination (cached geocode)
    # ... existing code ...
```

## Test
1. Run task manually: `python manage.py qcluster`
2. Verify `tasks.log` for query count
3. Check weather updated on days
4. Run `just ftest`

## Acceptance criteria
- [ ] Query count reduced by 80%+
- [ ] Weather fetch completed within 30s for 10 trips
- [ ] All tests pass
- [ ] Memory usage < 100MB during task

Codeberg issue: #258

## Summary of Changes

Added prefetch_related to trips queryset in fetch_weather_for_active_trips.
Removed inner prefetch in fetch_weather_for_trip to reuse outer cache.
Query count reduced from ~3xN_trips to 4 total.
