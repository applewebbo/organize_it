---
# organize_it-gvdb
title: Authorization helper for collaborators
status: completed
type: task
priority: normal
created_at: 2026-04-04T06:19:39Z
updated_at: 2026-04-04T06:42:49Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-sf5l
---

Centralized authorization utilities for collaborator access control.

## Todo
- [x] get_trip_or_404(pk, user): Trip owned by OR collaborated by user
- [x] get_trip_for_owner_or_404(pk, user): only owner
- [x] accessible_trips_qs(user): queryset usata inline nelle views
- [x] Aggiornare tutte le mutation views (events, stays, main transfers) a usare i nuovi helper
- [x] Proteggere trip detail/edit: collaboratori vedono la trip ma non possono cambiare titolo/date/destinazione

## Summary of Changes

Aggiunti helper in trips/utils.py: accessible_trips_qs(user), get_trip_or_404(pk, user), get_trip_for_owner_or_404(pk, user). Aggiornate ~50 occorrenze in views.py: trip detail/day/events/stays/main transfers usano accessible_trips_qs; trip delete/update/archive/share links usano get_trip_for_owner_or_404; ShareLink revoke mantiene trip__author=request.user.
