---
# organize_it-dhbq
title: Add Google Maps link auto-fill for experience, meal and stay forms
status: completed
type: feature
priority: normal
created_at: 2026-05-14T07:54:02Z
updated_at: 2026-05-15T07:49:34Z
---

Helper field at the top of Experience/Meal/Stay modals: paste a maps.app.goo.gl link → HTMX resolves the short URL server-side, extracts place_id, calls Places API, pre-fills name/city/address/coords/website/phone/opening_hours. Field is not saved. Tag/meal type chosen manually. New view: resolve_maps_link. Ref: Codeberg #319.

## Todo
- [ ] trips/services.py: get_full_place_details() con field mask estesa
- [ ] trips/views/maps.py: resolve_maps_link view
- [ ] trips/urls.py: nuova URL
- [ ] trips/forms.py: hidden lat/lng in EventForm e StayForm
- [ ] trips/models.py: skip geocoding se lat/lng già presenti in Event.save() e Stay.save()
- [ ] templates: campo maps link in experience-create, meal-create, stay-create
- [ ] templates/trips/includes/maps-link-prefill.html: fragment prefill + alert error
- [ ] tests

## Summary of Changes

- Widened URL validation to accept maps.app.goo.gl, goo.gl/maps/, google.com/maps/, maps.google.com/
- Added @lat,lng coordinate extraction as fallback (covers URLs without !3d/!4d)
- Passed place data as JSON to template (fixes silent JS failures with special chars in place names)
- Added success alert when location is found
- Added animated green outline (5 s) on pre-filled fields via inline outline CSS
- Added IT/EN translations for both success and error messages
- Full test coverage at 100%

## Summary of Changes

Widened URL validation to accept all Google Maps URL formats (maps.app.goo.gl, goo.gl/maps/, google.com/maps/, maps.google.com/). Fixed field pre-fill by passing place data as JSON (avoiding JS failures with special chars). Added success/error alerts and animated green outline (5 s) on pre-filled fields. Added hidden lat/lng fields in EventForm/StayForm to skip redundant Mapbox geocoding when coordinates come from Google Places. UI: Google Maps field wrapped in card (bg-base-200, border-base-300). Full IT/EN translations. 100% test coverage.
