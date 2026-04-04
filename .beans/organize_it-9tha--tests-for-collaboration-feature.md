---
# organize_it-9tha
title: Tests for collaboration feature
status: todo
type: task
created_at: 2026-04-04T06:20:22Z
updated_at: 2026-04-04T06:20:22Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-jbg4
    - organize_it-v0xp
    - organize_it-4wmu
    - organize_it-trrx
---

100% coverage tests for all collaboration components.

## Todo
- [ ] Test TripCollaboration model: colore automatico, unicità, relazioni
- [ ] Test TripInvitation model: token, scadenza, accepted
- [ ] Test authorization helpers: owner, collaboratore, utente estraneo
- [ ] Test add/remove collaborator views
- [ ] Test search_user_by_email: trovato, non trovato
- [ ] Test invitation flow: creazione, accept con utente loggato, accept dopo registrazione
- [ ] Test badge: last_modified_by su event/stay/main transfer
- [ ] Test trip list: due sezioni separate
- [ ] Test fav_trip con trip condiviso
- [ ] Test notifiche email
