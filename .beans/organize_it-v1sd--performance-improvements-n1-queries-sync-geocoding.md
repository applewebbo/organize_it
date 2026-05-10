---
# organize_it-v1sd
title: 'Performance improvements: N+1 queries, sync geocoding, missing prefetch and indexes'
status: completed
type: task
priority: normal
created_at: 2026-05-01T08:11:11Z
updated_at: 2026-05-10T11:31:56Z
---

Performance audit. Codeberg issue #293. Target release: 2026.7.1

## Todo
- [x] Aggiungere prefetch_related('days') in trip_list view (views.py:95-127)
- [x] Eliminare N+1 in Day.next_day/prev_day (models.py:416-433, templatetags/trip_tags.py:123-175)
- [ ] Spostare geocoding Mapbox in background task → issue #305, deferred
- [ ] Spostare download Unsplash in background task → issue #306, deferred
- [x] Usare bulk_update in check_trips_status() (tasks.py:55-88)
- [x] Aggiungere cache su Google Places API (services.py)
- [x] Deduplicare get_profile() nella stessa view (views.py:102,176,227)
- [x] Aggiungere db_index=True su enriched in Event e Stay

## Summary of Changes

- prefetch_related('days') aggiunto alle 3 queryset di trip_list
- check_trips_status() refactored: ora usa bulk_update invece di save() per trip, filtra in anticipo i trip archiviati e senza date
- db_index=True su enriched in Event e Stay (migrazione 0025)
- get_profile() deduplicato in trip_detail (ora una sola chiamata) e semplificato in day_detail

Rimandati a futuro: geocoding async, Unsplash async, cache Google Places.
