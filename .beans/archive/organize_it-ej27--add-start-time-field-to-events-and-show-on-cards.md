---
# organize_it-ej27
title: Add start_time field to events and show on cards
status: completed
type: feature
priority: normal
created_at: 2026-05-05T17:44:44Z
updated_at: 2026-05-06T06:05:57Z
---

Add optional start_time (TimeField) to Event model. Show start_time and estimated_duration on event cards and map list item when present. Issue #299

## Tasks

- [ ] Aggiungere start_time a Event model
- [ ] Creare migrazione
- [ ] Aggiornare ExperienceForm e MealForm
- [ ] Aggiornare event.html (card)
- [ ] Aggiornare event_list_item.html (mappa)
- [ ] Aggiornare/aggiungere traduzioni
- [ ] Test 100% coverage

## Tasks

- [x] Add start_time to Event model
- [x] Create migration
- [x] Update ExperienceForm and MealForm
- [x] Update event.html card
- [x] Update event_list_item.html
- [x] Translations
- [x] Tests 100% coverage

## Summary of Changes

Added start_time (TimeField) to Event model with migration. Updated ExperienceForm/MealForm layout to show start_time and duration side by side. Event cards show start_time (ph-clock) and estimated_duration (ph-timer) with matching icon color and opacity-70. event_list_item.html updated with trip_tags load. Fixed fuzzy translations for Start time, Experience type, Not specified.
