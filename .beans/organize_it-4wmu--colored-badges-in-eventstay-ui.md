---
# organize_it-4wmu
title: Colored badges in event/stay UI
status: todo
type: task
priority: normal
created_at: 2026-04-04T06:20:01Z
updated_at: 2026-04-06T17:27:53Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-gvdb
---

Show who added/last-modified each event, stay and main transfer with collaborator color badge.

## Todo
- [x] Badge component: pallino colorato con nome nel tooltip (title); solo se trip ha collaboratori
- [x] Event.last_modified_by = request.user in add_experience, add_meal (creazione)
- [x] Stay.author = request.user in add_stay (creazione)
- [x] MainTransfer.last_modified_by = request.user in save_main_transfer (solo nuovi transfer)
- [x] Mostrare badge in day-detail, trip-detail, shared-trip-detail (read-only) — solo se il trip ha almeno un collaboratore
- [x] Badge usa colore da TripCollaboration; owner ha colore neutro/default

## Todo aggiuntivi (da implementare)
- [ ] Aggiungere autore trip a collab_colors con colore neutro bg-base-300 (solo se trip ha collaboratori)
- [ ] Template: nascondere badge se event.last_modified_by == request.user (non mostrare il proprio badge)
- [ ] Stesso per stay.author e transfer.last_modified_by

## Summary of Changes

- Added `dict_get` and `user_display_name` template filters (Profile.first_name → email prefix fallback)
- Views set `last_modified_by`/`author` only at creation (add_experience, add_meal, add_stay, save_main_transfer new only)
- Added `collab_colors` dict to trip_detail, day_detail, main_transfers_section, shared_trip_detail views
- Created `_collab-badge.html` include: ph-user-circle icon with collaboration color + DaisyUI tooltip
- Badge visible only when trip has at least one collaborator
- 267 tests, 100% coverage maintained
