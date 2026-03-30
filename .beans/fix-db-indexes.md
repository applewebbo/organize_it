---
name: "Add missing database indexes"
title: "Add missing database indexes"
description: |
  Add indexes to the database to optimize the most frequent queries.

  ## Indexes to add:

  ### Trip model (`trips/models.py`)
  - `author, status` - For filter in `get_trips()`
  - `author, -start_date` - For list ordering

  ### Event model (`trips/models.py`)
  - `day, -start_time` - For reverse ordering
  - `trip` - For filter on `all_events`

  ### Stay model (`trips/models.py`)
  - `place_id` - For enrichment lookup

  ### Day model (`trips/models.py`)
  - `trip, date` - For filter and day ordering

  ## Test:
  - Create migration with `python manage.py makemigrations`
  - Verify with `EXPLAIN ANALYZE` queries before/after
  - Test on dataset with 100+ trips

  ## Notes:
  - Indexes increase disk space but improve reads
  - In production, apply during low-traffic hours
labels: ["performance", "database", "priority-1"]
priority: 1
order: 1
estimated_time: "15m"
---

# Add missing database indexes

## Objective
Improve query performance by adding strategic indexes.

## Required changes

### 1. Trip Model
```python
class Meta:
    ordering = ("status",)
    indexes = [
        models.Index(fields=["trip", "direction"]),  # existing
        models.Index(fields=["author", "status"]),  # NEW
        models.Index(fields=["author", "-start_date"]),  # NEW
    ]
```

### 2. Event Model
```python
class Meta:
    ordering = ["start_time"]
    indexes = [
        models.Index(fields=["day_id", "start_time"]),  # existing
        models.Index(fields=["day", "-start_time"]),  # NEW
        models.Index(fields=["trip"]),  # NEW
    ]
```

### 3. Stay Model
```python
class Meta:
    # add Meta if not exists
    indexes = [
        models.Index(fields=["place_id"]),  # NEW
    ]
```

### 4. Day Model
```python
class Meta:
    # add Meta if not exists
    indexes = [
        models.Index(fields=["trip", "date"]),  # NEW
    ]
```

## Steps
1. Modify models in `trips/models.py`
2. Create migration: `just makemigrations`
3. Apply migration: `just migrate`
4. Test with `just ftest`

## Acceptance criteria
- [ ] Migration created and applicable
- [ ] All tests pass
- [ ] Verified improvement with EXPLAIN ANALYZE
