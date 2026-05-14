---
# organize_it-4hk8
title: Add free tags to events/stays, display as banner
status: completed
type: feature
priority: normal
created_at: 2026-05-09T13:47:05Z
updated_at: 2026-05-12T07:12:01Z
---

Allow users to add free-form reusable tags to events and stays. Tags should be displayed as banners/badges on the event/stay cards. Tags should be reusable across events/stays (autocomplete from existing tags). Separate from meal type - no changes to the current meal category system.

Codeberg issue: #312

## Summary of Changes

- Added `tag` CharField (max 20 chars) to `Event` model (migration 0027)
- New HTMX endpoint `tag-suggestions` for per-user autocomplete
- `ExperienceForm`: campo tag (label 'Tipo') sostituisce il dropdown tipo; autocomplete inline
- `MealForm`: mantiene dropdown tipo, nessun tag
- Badge verde scuro (`bg-emerald-800`) sulla card, badge info nella modale e enrich-preview
- Tipo experience nascosto da modale e enrich-preview (solo tag mostrato)
- `|capfirst` su tutti i badge tag
