---
# organize_it-sf5l
title: Model changes for collaboration
status: todo
type: task
created_at: 2026-04-04T06:19:32Z
updated_at: 2026-04-04T06:19:32Z
parent: organize_it-z5rm
---

Add TripCollaboration through model (user, trip, color, added_at, added_by). Add TripInvitation model (token UUID, trip, email, invited_by, expires_at, is_accepted). Add Stay.author + Stay.last_modified_by FKs. Add Event.last_modified_by FK. Change Profile.fav_trip from OneToOneField to ForeignKey. Migration.

## Todo
- [ ] TripCollaboration model con palette colori predefinita (8 colori), assegnazione automatica colore libero
- [ ] TripInvitation model con token UUID e scadenza
- [ ] Stay.author (FK nullable, SET_NULL) + Stay.last_modified_by (FK nullable, SET_NULL)
- [ ] Event.last_modified_by (FK nullable, SET_NULL)
- [ ] Profile.fav_trip: OneToOneField → ForeignKey (migration con preserve data)
- [ ] Creare e applicare migration
