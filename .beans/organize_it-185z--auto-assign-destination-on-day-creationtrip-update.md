---
# organize_it-185z
title: Auto-assign destination on Day creation/trip update
status: completed
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T05:50:54Z
parent: organize_it-h7o7
---

Update update_trip_days signal to set Day.destination = trip.destination for new days. If trip.destination changes, update days that still have the old trip destination (skip customized ones). Use in-signal cache dict to geocode each unique destination only once via Mapbox.

## Summary of Changes\n\n- Added pre_save signal capture_trip_old_destination to store old destination before save\n- Updated update_trip_days signal: new days receive trip.destination with geocoding; existing days with old destination are updated when trip.destination changes; customized days are skipped\n- _geocode_destination helper with in-signal cache dict (one API call per unique destination)
