---
# fix
title: Fix N+1 queries in templates
status: completed
type: task
priority: "1"
created_at: 2026-03-30T13:06:33Z
updated_at: 2026-03-30T16:01:03Z
---

# Fix N+1 queries in templates

## Objective
Reduce query count from ~25 to ~8 per page.

## Required changes

### 1. `trips/views.py` - trip_detail (line ~131)
```python
qs = Trip.objects.prefetch_related(
    Prefetch(
        "days__events",
        queryset=annotate_event_overlaps(
            Event.objects.select_related("experience", "meal")
        ).order_by("start_time"),
    ),
    "days__stay",
    "main_transfers",
).select_related("author")
```

### 2. `trips/views.py` - shared_trip_detail (line ~2558)
```python
days = link.trip.days.prefetch_related(
    Prefetch(
        "events",
        queryset=Event.objects.select_related("experience", "meal")
        .annotate_event_overlaps()
        .order_by("start_time"),
    ),
    "stay",
)
```

### 3. `trips/utils.py` - get_trips (line ~52)
```python
# For fav_trip and latest_trip, add:
Prefetch(
    "days__events",
    queryset=annotate_event_overlaps(
        Event.objects.select_related("experience", "meal")
    ).order_by("start_time"),
),
```

### 4. `trips/views.py` - day_detail (line ~182)
```python
qs = Day.objects.prefetch_related(
    Prefetch(
        "events",
        queryset=annotate_event_overlaps(
            Event.objects.select_related("experience", "meal", "transfer_from__to_event")
        ).order_by("start_time"),
    ),
    "stay",
    "trip__main_transfers",
).select_related("trip__author")
```

## Test
1. Enable Django Debug Toolbar
2. Load trip with 10+ days and 50+ events
3. Verify query count is < 10
4. Run `just ftest`

## Acceptance criteria
- [ ] Query count reduced by 60%+
- [ ] All tests pass
- [ ] Debug Toolbar shows no N+1 warnings

Codeberg issue: #254

## Summary of Changes\n\nEliminated N+1 queries in trip_detail:\n- stay_transfer_out/in template tags now use prefetched reverse OneToOneField (transfer_from/transfer_to) instead of DB queries per day\n- Added prefetch 'days__stay__transfer_from' and 'days__stay__transfer_to' in trip_detail view and get_trips utility\n- Added test for stay_transfer_out when no transfer exists
