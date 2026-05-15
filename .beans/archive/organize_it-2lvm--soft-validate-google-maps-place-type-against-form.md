---
# organize_it-2lvm
title: Soft-validate Google Maps place type against form type
status: completed
type: feature
priority: normal
created_at: 2026-05-15T07:49:38Z
updated_at: 2026-05-15T08:27:17Z
---

Show a dismissible warning alert when resolving a Maps link if the place type mismatches the form: Stay warns if non-lodging, Meal warns if non-food, Experience warns only if lodging or food place. Fields are pre-filled regardless.

## Todo
- [x] Add `types` to `FULL_DETAILS_FIELD_MASK` in services.py and include in `PlaceFullDetails`
- [x] Include `types` in `place_data_json` from `resolve_maps_link` view
- [x] Pass `form_type` via `hx-vals` on each form's Search button
- [x] Add mismatch detection logic in view (or template)
- [x] Add warning alert in `maps-link-prefill.html`
- [x] Add IT/EN translations for warning messages
- [x] Tests for each mismatch scenario
- [x] 100% coverage

## Summary of Changes

Added `types` field to `PlaceFullDetails` and `FULL_DETAILS_FIELD_MASK`. Added `_LODGING_TYPES`, `_FOOD_TYPES` constants and `_place_type_warning()` helper in views/maps.py. Updated `resolve_maps_link` to read `form_type` from POST and return `type_warning` code. Template shows amber warning alert below success alert for mismatches. Each form passes `form_type` via `hx-vals`. Full IT/EN translations. 11 new tests, 100% coverage maintained.
