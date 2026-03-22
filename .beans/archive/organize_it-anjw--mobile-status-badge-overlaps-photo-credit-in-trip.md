---
# organize_it-anjw
title: 'Mobile: status badge overlaps photo credit in trip detail'
status: completed
type: bug
priority: normal
created_at: 2026-03-22T11:57:34Z
updated_at: 2026-03-22T13:42:48Z
---

In the mobile view of trip-detail.html, the trip status badge (bottom-right) overlaps the Unsplash photo attribution badge (bottom-left) when both are visible. Fix: move status badge to top-right of the image.

## Summary of Changes

Moved trip status badge from `bottom-3 right-3` to `top-3 right-3` in trip-detail.html to avoid overlap with Unsplash photo attribution badge. Fixed in v2026.4.1 (fix #239).
