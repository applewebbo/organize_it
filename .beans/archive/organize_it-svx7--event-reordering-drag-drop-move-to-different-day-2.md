---
# organize_it-svx7
title: 'Event reordering: drag & drop + move to different day (#282)'
status: completed
type: feature
priority: normal
created_at: 2026-04-23T13:45:01Z
updated_at: 2026-04-29T07:10:28Z
parent: organize_it-9ma2
---

SortableJS on sm+. Order saved to DB via HTMX. Save button after drag. Modal to move event to different day or unassign.

## Summary of Changes

- Added order field to Event model for drag & drop
- Added reorder_events POST endpoint accepting JSON {order: [pk...]}
- Auto-assigns order on add_experience/add_meal
- Updated SimpleTransfer ordering to use order field
- 100% test coverage maintained
