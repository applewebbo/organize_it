---
# organize_it-01ey
title: Replace SimpleTransfer with Google Maps directions button (#287)
status: completed
type: feature
priority: normal
created_at: 2026-04-29T13:38:36Z
updated_at: 2026-04-30T05:54:28Z
---

Remove SimpleTransfer model/views/tests/migrations. Replace inter-event transfer button with mobile-only Google Maps link (directions from current location to event address). Keep button icon, show only on mobile.

## Summary of Changes

- Rimosso modello SimpleTransfer, view, form, template e tutti i test correlati
- Aggiunto bottone Google Maps directions (mobile-only) su event_list_item
- Aggiunta copertura 100% per StayTransfer/MainTransferConnection views, forms e widget
- Creata migrazione 0016_remove_simpletransfer
