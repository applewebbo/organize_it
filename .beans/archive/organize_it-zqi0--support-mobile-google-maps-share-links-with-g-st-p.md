---
# organize_it-zqi0
title: Support mobile Google Maps share links with ?g_st= parameter
status: completed
type: bug
priority: normal
created_at: 2026-05-16T10:53:29Z
updated_at: 2026-05-16T11:00:09Z
---

resolve_maps_link fails when maps.app.goo.gl?g_st=ic expands to ?q= format instead of /maps/place/ path. Need to handle the alternative URL format in the fallback. Issue #322.

## Summary of Changes

- Added ?q= URL format detection in resolve_maps_link fallback path
- Extracts place name from q= parameter and optional coordinates from ll= parameter
- Excludes generic /search/ URLs to avoid false positives
- Fixes mobile share links (maps.app.goo.gl?g_st=ic) that expand to query format
