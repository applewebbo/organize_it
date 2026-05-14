---
# organize_it-vv6s
title: Refactor trips/views.py into multiple focused modules
status: completed
type: task
priority: normal
created_at: 2026-05-12T13:36:11Z
updated_at: 2026-05-14T06:36:45Z
---

trips/views.py has grown to 3337 lines and should be split into focused modules by domain (e.g. trip views, day views, event views, transfer views, map views, etc.) to improve maintainability and navigability. All imports and URL routing must remain compatible.

Codeberg issue: #313

## Piano di lavoro\n\n- [ ] Creare struttura  package\n- [ ]  - trip views principali\n- [ ]  - day views\n- [ ]  - event views + note\n- [ ]  - stay views + note\n- [ ]  - transfer views\n- [ ]  - collaborator/share views\n- [ ]  - map views + geocoding\n- [ ]  - utility views\n- [ ]  - re-export tutto\n- [x] Verificare test 100% coverage

## Summary of Changes\n\nSplit monolithic `trips/views.py` (3384 lines) into 8 focused modules under `trips/views/`:\n- `trips.py` — trip CRUD, validate_dates, search_trip_images, shared_trip_detail\n- `days.py` — day detail, event reordering\n- `events.py` — event CRUD, notes, enrichment, tag suggestions\n- `stays.py` — stay CRUD, notes, enrichment\n- `transfers.py` — main/stay transfers, airport/station search, transfer info\n- `collaborators.py` — sharing, collaborators, invitations\n- `maps.py` — Leaflet map, Google Places search, geocoding, stages\n- `utils.py` — log file viewer\n\n`__init__.py` re-exports all public views for full backward compatibility. Updated mock patch paths in 6 test files.
