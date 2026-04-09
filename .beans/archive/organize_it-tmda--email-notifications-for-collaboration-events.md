---
# organize_it-tmda
title: Email notifications for collaboration events
status: completed
type: task
priority: normal
created_at: 2026-04-04T06:20:12Z
updated_at: 2026-04-07T18:55:50Z
parent: organize_it-z5rm
---

Send email notifications for collaboration-related events.

## Todo
- [x] Notifica a utente registrato quando viene aggiunto come collaboratore
- [x] Notifica all'owner quando un invitato accetta e si registra
- [x] Template email: aggiunto come collaboratore (con link alla trip)
- [x] Template email: invito a registrarsi (con link accept_invitation)

## Summary of Changes

Implemented email notifications for collaboration events:
- Email to registered user when added as collaborator (with trip link)
- Invite by email for non-registered users (creates TripInvitation + sends email with accept link)
- Accept invitation view (marks invitation accepted, creates TripCollaboration, notifies owner)
- 3 HTML email templates with i18n support
- Enabled "Invite by email" button in collab search result UI
- 16 new tests, 100% coverage maintained
