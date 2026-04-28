---
# organize_it-y5kk
title: Remove collaboration badges from event/stay/transfer cards
status: completed
type: task
priority: normal
created_at: 2026-04-28T13:21:48Z
updated_at: 2026-04-28T13:31:07Z
---

Issue #285: remove collab badge rendering from all templates, remove collab_colors context and select_related last_modified_by from views

## Summary of Changes\n\nRimossi tutti i badge collaboratore da templates (day-list-content, stays-section, main-transfers, shared-trip-detail). Rimossi collab_colors e viewer_id da 5 views. Rimossi select_related last_modified_by superflui. Rimossi 10 test correlati.
