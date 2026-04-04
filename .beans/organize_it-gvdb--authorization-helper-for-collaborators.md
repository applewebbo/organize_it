---
# organize_it-gvdb
title: Authorization helper for collaborators
status: todo
type: task
created_at: 2026-04-04T06:19:39Z
updated_at: 2026-04-04T06:19:39Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-sf5l
---

Centralized authorization utilities for collaborator access control.

## Todo
- [ ] get_trip_for_user(trip_id, user): Trip owned by OR collaborated by user
- [ ] can_edit_trip_details(trip, user): only owner
- [ ] can_edit_trip_content(trip, user): owner OR collaborator
- [ ] Aggiornare tutte le mutation views (events, stays, main transfers) a usare i nuovi helper
- [ ] Proteggere trip detail/edit: collaboratori vedono la trip ma non possono cambiare titolo/date/destinazione
