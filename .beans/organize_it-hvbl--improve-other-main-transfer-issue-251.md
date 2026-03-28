---
# organize_it-hvbl
title: 'Improve Other main transfer - issue #251'
status: completed
type: feature
priority: normal
created_at: 2026-03-28T12:16:28Z
updated_at: 2026-03-28T12:25:53Z
---

Add vehicle_type field to OtherMainTransferForm, remove quick-fill and home address pre-fill, improve type selection icon. See issue #251.

## Summary of Changes

- Added vehicle_type optional field to OtherMainTransferForm (stored in type_specific_data)
- Removed quick-fill suggestions and home_address pre-fill for OTHER type
- Removed departure pre-fill from arrival for OTHER type
- Updated type selection icon: ph-boat / ph-bus
- Shows vehicle_type in transport detail view
- Italian translations: 'Tipo di mezzo', placeholder 'es. Traghetto per Venezia, Flixbus per Milano'
- 100% test coverage maintained
