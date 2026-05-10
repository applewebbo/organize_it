---
# organize_it-e75x
title: 'Refactor transfer duration/distance: rename fields, new semantics, UI improvements'
status: completed
type: task
priority: normal
created_at: 2026-05-09T05:56:43Z
updated_at: 2026-05-10T11:35:09Z
---

Rename Day.transfer_duration_to_next→from_prev, change calculate_day_transfer to save on first day of arriving stage, update create_stage/delete_stage logic, align city-results UI with address-results pattern, add Nominatim search to trip form

## Summary of Changes\n\nCampi rinominati da transfer_duration_to_next/transfer_distance_to_next a transfer_duration_from_prev/transfer_distance_from_prev. calculate_day_transfer aggiornato per salvare sul primo giorno dello stage in arrivo. UI city-results allineata al pattern address-results.
