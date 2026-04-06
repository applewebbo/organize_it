---
# organize_it-jbg4
title: Collaborator management UI
status: completed
type: task
priority: normal
created_at: 2026-04-04T06:19:47Z
updated_at: 2026-04-05T07:12:53Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-gvdb
---

Owner UI to add/remove collaborators from trip detail page.

## Todo
- [x] Search by email (HTMX): utente registrato → mostra card con nome + colore assegnato + bottone Aggiungi
- [x] Se email non trovata → bottone "Invita via mail"
- [x] Sezione collaboratori in trip detail: lista con badge colorati + bottone rimuovi (solo owner)
- [x] Assegnazione automatica primo colore libero della palette alla creazione
- [x] View add_collaborator (POST, owner only)
- [x] View remove_collaborator (POST, owner only) - non cancella i dati aggiunti
- [x] View search_user_by_email (GET, HTMX)

## Summary of Changes

- Added `badge_bg_class` property to `TripCollaboration` model (+ `COLOR_BADGE_CLASSES` dict)
- Added 3 views: `search_user_by_email`, `add_collaborator`, `remove_collaborator`
- Added 3 URL patterns under `trips/<int:trip_id>/collaborators/`
- Created `templates/trips/includes/collaborators-section.html` (list + search form, owner-only actions)
- Created `templates/trips/includes/collab-search-result.html` (HTMX search result fragment)
- Updated `trip-detail.html` to include collaborators section
- Prefetch `collaborations` with `user__profile` in `trip_detail` view
- Updated `populate_trips` to create 2 users with a shared trip each
- 22 new tests, 100% coverage maintained
