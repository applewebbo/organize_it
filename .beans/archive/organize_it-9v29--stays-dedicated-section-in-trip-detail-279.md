---
# organize_it-9v29
title: Stays dedicated section in trip detail (#279)
status: completed
type: feature
priority: normal
created_at: 2026-04-23T13:45:01Z
updated_at: 2026-04-23T14:04:10Z
parent: organize_it-9ma2
---

Dedicated stays section below main transfers. All stays in sequence + add button, always visible even if empty.

## Todo
- [x] Aggiungere stays al context di trip_detail
- [x] Nuova view add_stay_for_trip (trip_pk invece di day_id)
- [ ] Nuovo URL trips/<int:trip_pk>/stays/create
- [ ] Nuovo template trips/includes/stays-section.html
- [ ] Aggiungere sezione in trip-detail.html dopo i main transfers
- [ ] Rimuovere stay info da day-list-content.html
