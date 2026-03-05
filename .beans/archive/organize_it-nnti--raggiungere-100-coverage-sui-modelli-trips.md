---
# organize_it-nnti
title: Raggiungere 100% coverage sui modelli trips
status: completed
type: task
priority: normal
created_at: 2026-01-17T14:25:07Z
updated_at: 2026-01-18T19:52:26Z
---

## Obiettivo
Raggiungere il 100% di coverage su trips/models.py (attualmente al 94%)

## Linee Mancanti
1. L470->474: geocoding fallisce (branch Event.save)
2. L597: SimpleTransfer.google_maps_url ritorna None
3. L604->611: clean() SimpleTransfer - stesso evento/giorno
4. L622-624: clean() SimpleTransfer - stesso trip
5. L630->635: save() SimpleTransfer - from_event senza day/trip
6. L727: StayTransfer.arrival_time ritorna None
7. L742: StayTransfer.google_maps_url ritorna None
8. L749->756: clean() StayTransfer - stesso stay
9. L770-772: clean() StayTransfer - stesso trip
10. L779->790: save() StayTransfer - stays senza days

## Checklist
- [ ] Test geocoding fallito in Event.save
- [ ] Test SimpleTransfer.google_maps_url senza coordinate
- [ ] Test SimpleTransfer.clean() - stesso evento
- [ ] Test SimpleTransfer.clean() - stesso trip diverso
- [ ] Test SimpleTransfer.save() - eventi senza day/trip
- [ ] Test StayTransfer.arrival_time senza dati
- [ ] Test StayTransfer.google_maps_url senza coordinate
- [ ] Test StayTransfer.clean() - stesso stay
- [ ] Test StayTransfer.clean() - stesso trip diverso
- [ ] Test StayTransfer.save() - stays senza days
- [ ] Verificare coverage al 100%
