---
# organize_it-mm0i
title: Verify custom image upload flow and UI on trip
status: completed
type: task
priority: normal
created_at: 2026-05-05T17:24:14Z
updated_at: 2026-05-05T17:37:59Z
---

Review and improve UX/flow for uploading a custom cover image on a trip. Issue #298

## Summary of Changes\n\nImproved custom image upload UX in TripForm: replaced raw Django widget with Alpine.js custom uploader showing h-32 preview, converted mode toggle buttons to tabs-border style matching list/map tabs, unified mt-4 top margin on both search and upload sections, added mt-4 to warning disclaimer. Unsplash grid updated to 2-col mobile / 3-col desktop with h-32 cards. Image processing via process_trip_image confirmed working (resize to 1200x800, JPEG q85, landscape enforcement).
