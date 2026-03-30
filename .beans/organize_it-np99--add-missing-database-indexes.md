---
# organize_it-np99
title: Add missing database indexes
status: completed
type: task
priority: high
created_at: 2026-03-30T15:08:36Z
updated_at: 2026-03-30T15:12:37Z
---

Add indexes to optimize frequent queries in Trip, Event, Stay, Day models. Codeberg issue: #253

## Summary of Changes\n\nAdded 5 indexes:\n- Trip: (author, status), (author, -start_date)\n- Event: (trip_id)\n- Stay: (place_id)\n- Day: (trip, date)\n\nMigration: 0012_day_trips_day_trip_id_05f6eb_idx_and_more.py
