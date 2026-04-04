---
# fix
title: Add missing database indexes
status: scrapped
type: task
priority: "1"
created_at: 2026-03-31T06:02:32Z
updated_at: 2026-04-04T05:44:25Z
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
