---
# organize_it-k1ti
title: 'Simplify car transfer form - issue #249'
status: in-progress
type: feature
priority: normal
created_at: 2026-03-26T19:54:10Z
updated_at: 2026-03-26T19:57:58Z
---

Remove rental fields from car form, add home address to profile, implement quick-fill location lists for main transfers. See issue #249 for full spec.

## Todo

- [ ] Rimuovi `booking_reference` e `ticket_url` da modello `MainTransfer` + migration
- [ ] Aggiungi `home_address`, `home_address_latitude`, `home_address_longitude` a `Profile` + migration
- [ ] Geocodifica `home_address` on save in `accounts/models.py`
- [ ] Aggiungi campo a `ProfileUpdateForm` e template profilo
- [ ] Rimuovi `company`, `booking_reference`, `ticket_url` da `CarMainTransferForm`
- [ ] Rimuovi `company` da `OtherMainTransferForm`
- [ ] Rimuovi display `company`, `booking_reference`, `ticket_url` da `transport-detail.html`
- [ ] Rinomina label 'Indirizzo' → 'Località' nei form car/other
- [ ] Implementa quick-fill list andata (giorno 1) nel view e template car
- [ ] Implementa quick-fill list ritorno (ultimo giorno) nel view e template car
- [ ] Fallback a `trip.destination` se nessun evento
- [ ] Auto-populate `origin_address` con `profile.home_address` (andata)
- [ ] Auto-populate `destination_address` con `profile.home_address` (ritorno)
- [ ] Aggiorna/scrivi test copertura 100%
- [ ] Aggiorna/crea documentazione (docs/en/ e docs/it/)
