---
# organize_it-d9g4
title: Geocoding on Day.save()
status: in-progress
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T05:32:40Z
parent: organize_it-h7o7
---

Override Day.save() to geocode destination via Mapbox when destination field changes and coords are missing. If destination is cleared, clear lat/lng too.
