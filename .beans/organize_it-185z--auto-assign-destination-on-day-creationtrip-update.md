---
# organize_it-185z
title: Auto-assign destination on Day creation/trip update
status: in-progress
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T05:32:40Z
parent: organize_it-h7o7
---

Update update_trip_days signal to set Day.destination = trip.destination for new days. If trip.destination changes, update days that still have the old trip destination (skip customized ones). Use in-signal cache dict to geocode each unique destination only once via Mapbox.
