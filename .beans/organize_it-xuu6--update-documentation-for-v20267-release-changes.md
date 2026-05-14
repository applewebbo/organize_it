---
# organize_it-xuu6
title: Update documentation for v2026.7 release changes
status: completed
type: task
priority: normal
created_at: 2026-05-03T06:39:09Z
updated_at: 2026-05-14T07:44:35Z
---

Update docs to reflect all changes shipped in v2026.7: unified events section, stays section, map view, estimated duration, event reordering, role-based collaboration, participants section redesign, removal of SimpleTransfer and trip description.

## Todo

- [x] EN experiences.md: start_time opzionale, duration al posto di end_time, campo tag/type
- [x] EN meals.md: start_time opzionale, duration al posto di end_time
- [x] EN days.md: map view, riordinamento eventi, multi-destinazione/stage
- [x] EN transfers.md: rimuovere sezione Simple Transfers (rimosso dal modello)
- [x] EN collaboration.md: distinzione editor/viewer (can_edit), named participants
- [x] IT experiences.md: stesse modifiche versione EN
- [x] IT meals.md: stesse modifiche versione EN
- [x] IT days.md: stesse modifiche versione EN
- [x] IT transfers.md: stesse modifiche versione EN
- [x] IT collaboration.md: stesse modifiche versione EN

## Summary of Changes

Updated EN and IT user guide across 5 files per language to reflect v2026.7.x changes:
- experiences/meals: start_time ora opzionale, durata sostituisce end_time, campo tag libero con autocomplete
- days: sezione map view, riordinamento drag-and-drop, sezione multi-destinazione/stage
- transfers: rimossa la sezione Simple Transfers (il modello è stato eliminato)
- collaboration: distinzione editor/visualizzatore, partecipanti nominali senza account
Issue Codeberg: #318
