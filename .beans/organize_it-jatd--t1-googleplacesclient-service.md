---
# organize_it-jatd
title: 'T1: GooglePlacesClient service'
status: completed
type: task
priority: normal
created_at: 2026-04-22T13:07:01Z
updated_at: 2026-04-22T13:14:01Z
parent: organize_it-coiq
---

Estrarre logica Places da enrich_stay/enrich_event in trips/services.py con search_text() e get_place_details(). Issue #276.

## Summary of Changes
- Creato trips/services.py con GooglePlacesClient (search_text, get_place_details, search_place_id)
- Refactoring enrich_stay e enrich_event in views.py per usare il service
- 18 test con 100% coverage su services.py
