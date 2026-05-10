---
# organize_it-v1sd
title: 'Performance improvements: N+1 queries, sync geocoding, missing prefetch and indexes'
status: in-progress
type: task
priority: normal
created_at: 2026-05-01T08:11:11Z
updated_at: 2026-05-10T11:04:15Z
---

Performance audit. Codeberg issue #293. Target release: 2026.7.1

## Todo
- [ ] Aggiungere prefetch_related('days') in trip_list view (views.py:95-127)
- [ ] Eliminare N+1 in Day.next_day/prev_day (models.py:416-433, templatetags/trip_tags.py:123-175)
- [ ] Spostare geocoding Mapbox in background task (models.py:178-517)
- [ ] Spostare download Unsplash in background task (views.py:336-406)
- [ ] Usare bulk_update in check_trips_status() (tasks.py:55-88)
- [ ] Aggiungere cache su Google Places API (views.py:1748-1917)
- [ ] Deduplicare get_profile() nella stessa view (views.py:102,176,227)
- [ ] Aggiungere db_index=True su enriched in Event e Stay
