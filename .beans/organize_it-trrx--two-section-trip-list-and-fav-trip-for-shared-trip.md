---
# organize_it-trrx
title: Two-section trip list and fav_trip for shared trips
status: todo
type: task
created_at: 2026-04-04T06:20:07Z
updated_at: 2026-04-04T06:20:07Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-sf5l
---

Split trip list into own trips + shared trips. Extend fav_trip to include collaborated trips.

## Todo
- [ ] Aggiornare trip list view: query separata per owned vs collaborated trips
- [ ] Template trip list: due sezioni distinte con header "I miei viaggi" / "Condivisi con me"
- [ ] Aggiornare accounts/forms.py ProfileForm.fav_trip queryset: includere Trip dove user è collaboratore
- [ ] Aggiornare trips/utils.py get_home_context: includere collaborated trips in other_trips
- [ ] Aggiornare test fav_trip per la nuova constraint (ForeignKey, non UniqueField)
