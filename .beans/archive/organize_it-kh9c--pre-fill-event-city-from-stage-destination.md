---
# organize_it-kh9c
title: Pre-fill event city from stage destination
status: completed
type: bug
priority: normal
created_at: 2026-05-08T13:38:32Z
updated_at: 2026-05-10T11:35:09Z
parent: organize_it-h7o7
---

Event/stay forms always use trip.destination as city initial value. When creating an event from a day belonging to a custom stage, city should be pre-filled with the stage destination.

## Summary of Changes\n\nImplementata funzione _day_city(day) in views.py che restituisce day.destination se presente, altrimenti trip.destination. Usata come initial per il campo city nei form event/stay/stay-transfer.
