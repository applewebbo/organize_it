---
# organize_it-jwzg
title: Move Unsplash photo download to background task
status: completed
type: feature
priority: normal
created_at: 2026-05-16T11:10:14Z
updated_at: 2026-05-16T11:18:13Z
---

Extract download_unsplash_photo + process_trip_image from trip_create/trip_update views to a django-q2 background task. Issue #306.

## Summary of Changes

- Added download_trip_unsplash_photo task in trips/tasks.py
- Removed synchronous download from trip_create and trip_update views
- trip.save() happens immediately, then async_task is scheduled
- File upload takes priority and skips the async task
- Updated and added tests in test_tasks.py and test_trip_image_integration.py
