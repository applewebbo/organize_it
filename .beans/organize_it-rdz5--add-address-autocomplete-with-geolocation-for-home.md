---
# organize_it-rdz5
title: Add address autocomplete with geolocation for home address in profile settings
status: completed
type: feature
priority: normal
created_at: 2026-05-14T06:53:40Z
updated_at: 2026-05-14T14:14:57Z
---

The home address field in profile settings should support address autocomplete (like event/stay address fields) and store lat/lon for transfer distance calculations. Ref: Codeberg issue #317.

## Decisioni tecniche
- Autocomplete via Google Places API (server-side proxy, chiave mai esposta al frontend)
- Singolo campo home_address con dropdown suggerimenti HTMX
- Campi lat/lng nascosti compilati alla selezione
- Fallback geocoding al save() del modello solo se lat/lng assenti nel form
- Fallback cambiato da Mapbox a Google Places

## Todo
- [x] accounts/forms.py: aggiungere hidden fields lat/lng in ProfileUpdateForm
- [x] accounts/views.py: aggiungere vista autocomplete_home_address
- [x] accounts/urls.py: aggiungere URL per la nuova vista
- [x] accounts/models.py: fallback Mapbox mantenuto (si attiva solo senza lat/lng)
- [x] templates/account/includes/home-address-results.html: template fragment risultati
- [x] templates/account/profile.html: aggiungere Alpine.js + HTMX sul campo home_address
- [x] tests: aggiungere test per la nuova vista e il form

## Summary of Changes

Aggiunti autocomplete Google Places per home_address nel profilo utente:
- ProfileUpdateForm esteso con hidden fields lat/lng
- Vista HTMX autocomplete_home_address con GooglePlacesClient (min 3 char, max 5 risultati)
- Alpine component homeAddressForm: clearCoords() su input manuale, selectAddress() su selezione
- Template fragment con attribuzione Google Places
- Fallback Mapbox nel modello mantenuto per indirizzi digitati manualmente
- 100% coverage (1003 test)
Ref: Codeberg issue #317
