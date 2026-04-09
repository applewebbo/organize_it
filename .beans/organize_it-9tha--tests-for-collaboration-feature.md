---
# organize_it-9tha
title: Tests for collaboration feature
status: completed
type: task
priority: normal
created_at: 2026-04-04T06:20:22Z
updated_at: 2026-04-08T06:16:47Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-jbg4
    - organize_it-v0xp
    - organize_it-4wmu
    - organize_it-trrx
---

100% coverage tests for all collaboration components.

## Todo
- [x] Test TripCollaboration model: colore automatico, unicità, relazioni
- [x] Test TripInvitation model: token, scadenza, accepted
- [x] Test authorization helpers: owner, collaboratore, utente estraneo
- [x] Test add/remove collaborator views
- [x] Test search_user_by_email: trovato, non trovato
- [x] Test invitation flow: creazione, accept con utente loggato, accept dopo registrazione
- [x] Test badge: last_modified_by su event/stay/main transfer
- [x] Test trip list: due sezioni separate
- [x] Test fav_trip con trip condiviso
- [x] Test notifiche email
