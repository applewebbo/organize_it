---
# organize_it-coiq
title: Map-based event/stay creation with Leaflet + Google Places + HTMX
status: completed
type: epic
priority: normal
created_at: 2026-04-22T13:03:15Z
updated_at: 2026-04-28T12:48:21Z
---

Replace event/stay creation with interactive Leaflet map. Google Places via Django proxy, HTMX partials, unified map view across all days. Issue #276.

## Architettura

```
Google Places API (server-side only)
      ↕
Django service layer (GooglePlacesClient)
      ↕
Django views → HTML partials
      ↕
HTMX (swap DOM fragments)
      ↕
Leaflet.js (marker sync via data-* attributes)
```

## Stato attuale
- Leaflet.js già disponibile in /static/
- Google Places già usato per enrichment in views.py:1972+
- Folium genera mappe statiche server-side (da rimpiazzare)
- Mapbox geocoding sulle model.save() (da mantenere come fallback)
- Mappa per-day in day-map-content.html (da unificare)

## Tasks

### T1 - GooglePlacesClient service
Estrarre/refactoring logica Places da enrich_stay/enrich_event in un servizio riusabile trips/services.py con metodi search_text() e get_place_details().

### T2 - Unified map view
Nuova view + template per mappa unificata trip (tutti gli eventi di tutti i giorni + non assegnati). Sostituisce day-map-content.html con Leaflet interattivo.

### T3 - HTMX search endpoint
View POST /trips/<trip_pk>/map/search/ che chiama GooglePlacesClient e restituisce partial HTML _map_search_results.html con data-lat/lng/name/place-id.

### T4 - HTMX add-from-map endpoint
View POST /trips/<trip_pk>/map/add/ che riceve dati dal form hidden nei risultati e crea Experience/Meal/Stay/Transport nel DB. Restituisce partial aggiornato.

### T5 - Leaflet JS module
Modulo JS (static/js/trip-map.js) con initMap(), rebuildResultMarkers(), rebuildExistingMarkers(), htmx:afterSwap listener. Layer separati per risultati ricerca / eventi esistenti.

### T6 - Template mappa + partials
Template principale trip-map.html + partials: _map_search_results.html, _map_event_panel.html.

### T7 - Tests
Test per GooglePlacesClient (mock HTTP), test views HTMX search e add-from-map.

## Summary of Changes\n\nTutti i 7 task completati: GooglePlacesClient service, unified Leaflet map view, HTMX search/add endpoints, JS module, templates e tests.
