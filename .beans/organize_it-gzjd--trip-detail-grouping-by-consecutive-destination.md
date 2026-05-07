---
# organize_it-gzjd
title: Trip-detail grouping by consecutive destination
status: completed
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T06:44:13Z
parent: organize_it-h7o7
---

In trip-detail view, detect if all days share the same destination (or are all blank): if yes, keep current layout. If at least one differs, group days into consecutive destination blocks and render with section headers. Grouping is by consecutive run, not global uniqueness.

## Summary of Changes\n\n- Added group_days_by_destination() helper in utils.py: groups consecutive days by destination, returns None for single/empty destination (flat layout fallback)\n- Updated trip_detail view to compute day_groups and pass to context\n- Updated events-list-fragment.html: renders destination headers between groups when day_groups is set, falls back to flat layout otherwise
