---
# organize_it-0sli
title: 'Participants: role-based collaboration with edit permissions'
status: in-progress
type: feature
priority: normal
created_at: 2026-05-01T08:04:18Z
updated_at: 2026-05-02T06:11:22Z
---

Rename collaborators to participants and introduce role-based access. Codeberg issue #292.

## Spec

### Model
- Add `can_edit: BooleanField(default=True)` to `TripCollaboration`
- Migration: existing collaborators → `can_edit=True`
- Utenti senza account (invitati via email non registrati) → `can_edit=False` forzato

### Permissions
- Views che oggi controllano `request.user == trip.author` devono estendersi ai collaboratori con `can_edit=True`
- Collaboratori con `can_edit=False` possono solo vedere

### Form / Modal
- Aggiungere toggle can_edit nel modal di aggiunta collaboratore
- Email obbligatoria solo se `can_edit=True`
- Il proprietario può modificare `can_edit` di un collaboratore esistente senza rimuoverlo

### UI
- Badge partecipanti con sfondo diverso per ruolo:
  - `can_edit=True`: sfondo soft blu (es. `bg-blue-100 dark:bg-blue-900/30 border-blue-300`)
  - `can_edit=False`: sfondo soft grigio (es. `bg-base-200 border-base-300`)
- Etichetta unica: 'Partecipanti' per entrambi i ruoli
- Aggiornare tutte le label 'Collaborator' → 'Participant'

## Todo
- [x] Aggiungere campo `can_edit` al modello `TripCollaboration`
- [x] Creare e applicare migrazione (default `can_edit=True` per esistenti)
- [x] Forzare `can_edit=False` per utenti senza account al momento dell'invito
- [x] Estendere controlli permessi nelle view
- [ ] Aggiornare modal aggiunta con toggle ruolo ed email condizionale
- [x] Aggiungere possibilità di modificare ruolo senza rimuovere il partecipante
- [x] Aggiornare UI badge con colori per ruolo
- [x] Aggiornare label 'Collaborator' → 'Participant' ovunque

Target release: 2026.7
