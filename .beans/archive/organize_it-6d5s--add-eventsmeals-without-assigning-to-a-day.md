---
# organize_it-6d5s
title: Add events/meals without assigning to a day
status: completed
type: feature
priority: normal
created_at: 2026-05-06T06:15:56Z
updated_at: 2026-05-06T06:58:30Z
---

Allow users to add Experience and Meal events from the trip detail page without assigning them to a specific day. Orphaned events appear in the Others section and can be paired to a day later.

## Summary of Changes

- Added `add_experience_to_trip` and `add_meal_to_trip` views (trip_pk, no day)
- Added URL routes `add-experience-to-trip` and `add-meal-to-trip`
- Created templates `experience-create-unpaired.html` and `meal-create-unpaired.html`
- 'Other Things to Do' section now always visible with Add event dropdown
- events-section refreshes via `unpairedModified` HTMX trigger
- Added 'Nothing to do here.' empty state to day cards and Other Things to Do section
- Translations added to both .po files and compiled
