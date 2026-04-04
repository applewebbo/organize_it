---
# organize_it-trrx
title: Two-section trip list and fav_trip for shared trips
status: completed
type: task
priority: normal
created_at: 2026-04-04T06:20:07Z
updated_at: 2026-04-04T06:50:06Z
parent: organize_it-z5rm
blocked_by:
    - organize_it-sf5l
---

Split trip list into own trips + shared trips. Extend fav_trip to include collaborated trips.

## Todo
- [x] Aggiornare trip list view: query separata per owned vs collaborated trips
- [x] Template trip list: due sezioni distinte con header "I miei viaggi" / "Condivisi con me"
- [x] Aggiornare accounts/forms.py ProfileForm.fav_trip queryset: includere Trip dove user è collaboratore
- [x] Aggiornare trips/utils.py get_home_context: includere collaborated trips in other_trips
- [x] Aggiornare test fav_trip per la nuova constraint (ForeignKey, non UniqueField)

## Summary of Changes

trip_list view: aggiunta shared_trips queryset. fav_trip form: Q(author) | Q(collaborators) + distinct(). get_trips utils: base_qs include collaborated trips. Template: nuova sezione Shared with me con card autore.
