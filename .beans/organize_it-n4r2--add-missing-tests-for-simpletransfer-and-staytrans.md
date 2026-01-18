---
# organize_it-n4r2
title: Add missing tests for SimpleTransfer and StayTransfer clean methods
status: completed
type: task
priority: normal
created_at: 2026-01-18T12:10:44Z
updated_at: 2026-01-18T12:17:02Z
---

Add tests to cover missing branches in clean() methods:

## SimpleTransfer.clean()
- Test when from_event_id or to_event_id is None (skip first validation)
- Test when from_event.day_id or to_event.day_id is None (skip day validation)
- Test when from_event.trip_id or to_event.trip_id is None (skip trip validation)

## StayTransfer.clean()
- Test when from_stay_id or to_stay_id is None (skip first validation)
- Test when from_day or to_day not set (skip consecutive days validation)
- Test when from_day or to_day not set (skip same trip validation)

## Checklist
- [x] Add SimpleTransfer tests for None event IDs
- [x] Add SimpleTransfer tests for None day IDs
- [x] Add SimpleTransfer tests for None trip IDs
- [x] Add StayTransfer tests for None stay IDs
- [x] Add StayTransfer tests for missing days
- [x] Verify coverage on trips/models.py clean methods

## Results
Coverage increased from 98% to 99% on trips/models.py. All branches in SimpleTransfer.clean() and StayTransfer.clean() are now covered.

The remaining uncovered branch (154->157) is in Stay.save() method (city check) and is outside the scope of this task.
