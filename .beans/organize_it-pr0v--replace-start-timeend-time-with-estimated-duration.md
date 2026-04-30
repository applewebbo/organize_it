---
# organize_it-pr0v
title: Replace start_time/end_time with estimated duration (#281)
status: completed
type: feature
priority: normal
created_at: 2026-04-23T13:45:01Z
updated_at: 2026-04-29T07:10:28Z
parent: organize_it-9ma2
---

Experience & Meal only. estimated_duration in steps of 30min. Order by creation (then drag & drop via order field). Remove overlap logic. Migration required.

## Todo
- [ ] Add `estimated_duration` field to Event (nullable, for Experience/Meal)
- [ ] Add `order` field to Event for drag & drop ordering
- [ ] Remove overlap detection logic (annotate_event_overlaps)
- [ ] Update Event.Meta ordering to use `order`
- [ ] Create and run migration
- [ ] Update forms (Experience/Meal): replace start_time/end_time with estimated_duration
- [ ] Update views: auto-set order on event creation
- [ ] Update templates: remove time fields, add duration selector
- [ ] Add SortableJS drag & drop + HTMX save endpoint
- [ ] Update tests to 100% coverage

## Summary of Changes

- Removed start_time/end_time fields from Event model
- Added estimated_duration DurationField (nullable)
- Added order PositiveIntegerField for drag & drop ordering
- Added duration_display template tag
- Updated all templates and forms to use new fields
- Removed annotate_event_overlaps and related views
- Added reorder_events view with JSON endpoint
- 100% test coverage maintained

## Summary of Changes

- Removed start_time/end_time fields from Event model
- Added estimated_duration DurationField (nullable)
- Added order PositiveIntegerField for drag & drop ordering
- Added duration_display template tag
- Updated all templates and forms to use new fields
- Removed annotate_event_overlaps and related views
