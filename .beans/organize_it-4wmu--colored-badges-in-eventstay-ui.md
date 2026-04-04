---
# organize_it-4wmu
title: Colored badges in event/stay UI
status: todo
type: task
created_at: 2026-04-04T06:20:01Z
updated_at: 2026-04-04T06:20:01Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-gvdb
---

Show who added/last-modified each event, stay and main transfer with collaborator color badge.

## Todo
- [ ] Badge component (cotton): mostra first_name (fallback: email prefix) + pallino colorato
- [ ] Aggiornare save di Event: impostare last_modified_by = request.user (se collaboratore)
- [ ] Aggiornare save di Stay: impostare author = request.user alla creazione, last_modified_by alla modifica
- [ ] Aggiornare save di MainTransfer: last_modified_by alla modifica
- [ ] Mostrare badge in day-detail, trip-detail, shared-trip-detail (read-only)
- [ ] Badge usa colore da TripCollaboration; owner ha colore neutro/default
