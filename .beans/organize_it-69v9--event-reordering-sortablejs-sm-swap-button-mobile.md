---
# organize_it-69v9
title: 'Event reordering: SortableJS (sm+) + swap button (mobile) (#278)'
status: completed
type: feature
priority: normal
created_at: 2026-04-29T12:56:29Z
updated_at: 2026-04-29T13:35:52Z
---

Hybrid approach: SortableJS drag & drop on sm+ screens, swap-order button on mobile. Backend already ready (reorder_events view + order field). Need: SortableJS integration on events list, auto-save on drop, swap endpoint + mobile UI.

## Summary of Changes

- SortableJS drag & drop su sm+: inizializzato via DOMContentLoaded (defer-safe), re-inizializzato dopo ogni htmx:afterSettle
- Cursore grab/grabbing applicato via JS sui <li> draggabili
- Icona maniglia dots-six-vertical assoluta nell'angolo della card (sm+ only, zero impatto altezza)
- Endpoint swap-event-order-modal (GET) per modale mobile con nuvola di eventi colorati per tipo
- Endpoint swap-event-order (POST) per scambiare ordine tra due eventi
- Script order corretto in base.html: main.js prima di alpine per alpine:init listener
- 870 test, 100% coverage
