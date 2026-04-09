---
# organize_it-4c78
title: Improve populate_trips command
status: completed
type: task
priority: normal
created_at: 2026-04-04T05:53:08Z
updated_at: 2026-04-04T05:54:30Z
---

Modify populate_trips to generate: 1 completed, 2 impending, 1 not-started trip per user

## Summary of Changes\n\nSostituita variabile TRIPS_PER_USER con TRIP_DATE_CONFIGS: lista di tuple (start_offset, end_offset) che definisce esattamente i 4 viaggi creati per utente: 1 completato (-14/-10 giorni), 2 imminenti (1/4 e 3/6 giorni), 1 non iniziato (10/14 giorni).
