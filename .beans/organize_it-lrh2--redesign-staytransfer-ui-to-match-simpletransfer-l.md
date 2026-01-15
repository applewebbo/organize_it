---
# organize_it-lrh2
title: 'Redesign StayTransfer UI to match SimpleTransfer layout (for #226)'
status: in-progress
type: task
created_at: 2026-01-15T06:48:36Z
updated_at: 2026-01-15T06:48:36Z
---

Ripristinare il layout dello StayTransfer per renderlo simile al SimpleTransfer:

## Obiettivi
- Layout responsivo: 1 colonna su mobile, 2 colonne da sm+
- Eliminare il div separato con bottone aggiungi/visualizza
- Integrare bottone "Aggiungi" nello stay del giorno corrente
- Card compatta in fondo allo stay con: freccia verso stay successivo, nome stay, tipo di trasporto, bottoni mappa/elimina
- Visualizzare stay del giorno successivo nella griglia (se diverso)
- Bottone "Aggiungi Transfer" uguale a quello del SimpleTransfer

## Checklist
- [x] Modificare template day-list-content per layout 1/2 colonne
- [x] Integrare bottone "Aggiungi StayTransfer" in fondo allo stay (stile SimpleTransfer)
- [x] Creare card StayTransfer compatta con freccia, nome stay, icona trasporto, bottoni mappa/elimina
- [x] Rimuovere layout a 3 colonne
- [x] Aggiungere stay del giorno successivo nella griglia
- [ ] Testare layout su mobile e desktop
- [ ] Verificare funzionalità mappa ed elimina

## File modificati
- templates/trips/includes/day-list-content.html
