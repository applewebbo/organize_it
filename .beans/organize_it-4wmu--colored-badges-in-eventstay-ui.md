---
# organize_it-4wmu
title: Colored badges in event/stay UI
status: in-progress
type: task
priority: normal
created_at: 2026-04-04T06:20:01Z
updated_at: 2026-04-06T17:14:02Z
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
