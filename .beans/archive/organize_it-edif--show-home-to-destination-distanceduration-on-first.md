---
# organize_it-edif
title: Show home-to-destination distance/duration on first/last trip day (also without stages)
status: completed
type: feature
priority: normal
created_at: 2026-05-14T14:15:41Z
updated_at: 2026-05-14T18:44:51Z
---

Display estimated distance and duration between home address and trip destination on the first and last day of a trip. Currently this only works for trips with stays/stages; it should also work for trips without any stages, using the trip's destination directly. Ref: Codeberg issue #320.

## Todo
- [ ] trips/tasks.py: aggiungere trip.destination_latitude/longitude come fallback in _get_day_coords
- [ ] tests: aggiungere test per il nuovo fallback

## Summary of Changes

Aggiunto fallback in _get_day_coords: se il giorno non ha coordinate proprie (nessuna tappa/stay/evento geocodificato), usa destination_latitude/longitude del Trip. Aggiunto geocoding automatico della destinazione Trip nel segnale pre_save. Migrazione 0029. Implementato nel commit for #317.
