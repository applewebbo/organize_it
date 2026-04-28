---
# organize_it-7634
title: 'T3: HTMX search endpoint'
status: completed
type: task
priority: normal
created_at: 2026-04-22T13:07:03Z
updated_at: 2026-04-28T06:00:38Z
parent: organize_it-coiq
---

View POST /trips/<trip_pk>/map/search/ che chiama GooglePlacesClient, restituisce partial _map_search_results.html con data-* attributes. Issue #276.

## Summary of Changes\n\nGià implementato: view map_search in trips/views.py con endpoint POST /trips/<pk>/map/search/ che chiama GooglePlacesClient e restituisce partial HTML.
