---
# organize_it-jbg4
title: Collaborator management UI
status: todo
type: task
created_at: 2026-04-04T06:19:47Z
updated_at: 2026-04-04T06:19:47Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-gvdb
---

Owner UI to add/remove collaborators from trip detail page.

## Todo
- [ ] Search by email (HTMX): utente registrato → mostra card con nome + colore assegnato + bottone Aggiungi
- [ ] Se email non trovata → bottone "Invita via mail"
- [ ] Sezione collaboratori in trip detail: lista con badge colorati + bottone rimuovi (solo owner)
- [ ] Assegnazione automatica primo colore libero della palette alla creazione
- [ ] View add_collaborator (POST, owner only)
- [ ] View remove_collaborator (POST, owner only) - non cancella i dati aggiunti
- [ ] View search_user_by_email (GET, HTMX)
