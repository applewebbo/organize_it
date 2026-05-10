---
# organize_it-d9g4
title: Geocoding on Day.save()
status: completed
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T05:50:54Z
parent: organize_it-h7o7
---

Override Day.save() to geocode destination via Mapbox when destination field changes and coords are missing. If destination is cleared, clear lat/lng too.

## Summary of Changes\n\n- Added Day.save() override: geocodes destination via Mapbox when destination changes and coords missing; clears lat/lng when destination is cleared
