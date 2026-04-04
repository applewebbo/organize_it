---
# organize_it-v0xp
title: Invitation flow for non-registered users
status: todo
type: task
created_at: 2026-04-04T06:19:54Z
updated_at: 2026-04-04T06:19:54Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-sf5l
---

Email invitation flow for users not yet registered.

## Todo
- [ ] View invite_by_email (POST, owner only): crea TripInvitation con token + scadenza 7gg, invia email
- [ ] Template email invito con link a registrazione pre-compilata (?invitation=<token>)
- [ ] Hook post-registrazione allauth: se invitation token in sessione/URL, auto-add come collaboratore e segna accepted_at
- [ ] View accept_invitation (GET): valida token, se utente già loggato accetta direttamente, altrimenti redirect a signup con token
- [ ] Gestione token scaduto/già usato
