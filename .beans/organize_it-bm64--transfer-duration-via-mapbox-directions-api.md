---
# organize_it-bm64
title: Transfer duration via Mapbox Directions API
status: in-progress
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-08T13:38:30Z
parent: organize_it-h7o7
---

After any Day.destination change, calculate transfer_duration_to_next (minutes) and transfer_distance_to_next (km) for that day and the previous day using Mapbox Directions API driving profile. Store on Day. Show visual separator between destination groups in trip-detail (e.g. '~2h 30min | ~240 km → Napoli').

## Approach Change (2026-05-08)
Instead of relying on stay/event coordinates, geocode the stage destination directly at creation time with user-assisted city selection (Nominatim search → user picks correct result). Days store destination_latitude/destination_longitude. calculate_day_transfer uses these first, then falls back to stay/event coords.
