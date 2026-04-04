---
# organize_it-sf5l
title: Model changes for collaboration
status: completed
type: task
priority: normal
created_at: 2026-04-04T06:19:32Z
updated_at: 2026-04-04T06:33:14Z
parent: organize_it-z5rm
---

Add TripCollaboration through model (user, trip, color, added_at, added_by). Add TripInvitation model (token UUID, trip, email, invited_by, expires_at, is_accepted). Add Stay.author + Stay.last_modified_by FKs. Add Event.last_modified_by FK. Change Profile.fav_trip from OneToOneField to ForeignKey. Migration.

## Todo
- [x] TripCollaboration model con palette colori predefinita (8 colori), assegnazione automatica colore libero
- [x] TripInvitation model con token UUID e scadenza
- [x] Stay.author (FK nullable, SET_NULL) + Stay.last_modified_by (FK nullable, SET_NULL)
- [x] Event.last_modified_by (FK nullable, SET_NULL)
- [x] Profile.fav_trip: OneToOneField → ForeignKey (migration con preserve data)
- [x] Creare e applicare migration

## Summary of Changes

Aggiunti modelli TripCollaboration (with-model M2M con palette 8 colori e next_free_color), TripInvitation (token UUID, scadenza, is_valid). Aggiunti campi last_modified_by a Event/MainTransfer, author+last_modified_by a Stay. Trip.collaborators M2M via TripCollaboration. Profile.fav_trip da OneToOneField a ForeignKey. Migration 0013 (trips) e 0006 (accounts).
