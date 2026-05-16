---
# organize_it-lukz
title: Add HTMX polling placeholder for pending Unsplash image
status: completed
type: feature
priority: normal
created_at: 2026-05-16T11:20:10Z
updated_at: 2026-05-16T11:34:42Z
---

Show a loading spinner while the background Unsplash download task runs. Poll a new endpoint every 3s; swap in the image when ready. Applies to trip-list and trip-header-card. Issue #306.

## Summary of Changes

- Added `download_trip_unsplash_photo` background task in `trips/tasks.py`
- Both `trip_create` and `trip_update` set `image_metadata.pending=True` and clear image before scheduling async download
- Added `trip_image_status` HTMX polling view + URL (`trips/<pk>/image-status/`)
- Added `trip-image.html` reusable include with spinner when pending
- Added `trip-image-status-fragment.html` polling response fragment
- Updated `trip-list.html` and `trip-header-card.html` to use the new include
- 12 tests passing (TestTripImagePendingFlag + existing classes)
