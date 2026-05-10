---
# organize_it-smeo
title: Day destinations modal with cards
status: completed
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T13:22:27Z
parent: organize_it-h7o7
---

New HTMX view/modal accessible from trip-detail showing all days as cards. Each card shows day number, date, and editable destination field. Editing destination updates Day inline via HTMX and triggers transfer recalculation for adjacent days.

## Summary of Changes\n\n- New view trip_destinations: HTMX modal with day cards\n- New view update_day_destination: POST updates day.destination, GET returns card fragment\n- New templates: trip-destinations-modal.html, day-destination-card.html\n- Button in events-section.html header opens the modal\n- destinationModified HTMX trigger refreshes events-section after save

## Summary of Changes

- Redesigned trip destinations modal as 2-step stage flow (step 1: stage overview, step 2: create stage)
- Added create_stage and delete_stage views with HTMX
- Added get_trip_stages utility
- Moved stages button to trip header card (ph-line-segments icon, btn-primary)
- Stage cards: secondary color for main, neutral gray for custom
- Delete confirm replaces Add stage button at bottom via Alpine.js shared state
- Added translations for Events, Stages, %(count)s days in EN/IT
- Tests: CreateStageView, DeleteStageView, TestGetTripStages (100% coverage)
