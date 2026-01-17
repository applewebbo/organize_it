---
# organize_it-2rgh
title: Rimozione completa del modello Transport
status: in-progress
type: task
created_at: 2026-01-17T07:26:20Z
updated_at: 2026-01-17T07:26:20Z
---

Rimuovere il modello Transport (sottoclasse di Event per trasporti giornalieri) mantenendo MainTransfer intatto.

## Checklist

- [ ] Creare migrazione per rimuovere dati Transport dal DB
- [ ] Rimuovere modello Transport da models.py
- [ ] Rimuovere TransportForm da forms.py
- [ ] Rimuovere views e URLs relativi a Transport
- [ ] Rimuovere TransportAdmin da admin.py
- [ ] Aggiornare template tags (trip_tags.py)
- [ ] Aggiornare utils.py (get_event_instance)
- [ ] Rimuovere templates Transport
- [ ] Aggiornare/rimuovere test
- [ ] Aggiornare management command populate_trips
- [ ] Eseguire test per verificare
