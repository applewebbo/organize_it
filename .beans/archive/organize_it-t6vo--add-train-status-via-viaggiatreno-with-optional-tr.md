---
# organize_it-t6vo
title: Add train status via viaggiatreno with optional train number
status: completed
type: feature
priority: normal
created_at: 2026-03-23T10:52:55Z
updated_at: 2026-03-24T06:54:43Z
---

Issue #244 follow-up: optional train_number field in form, redirect view to viaggiatreno for specific train or station board, button active only on travel day

## Summary of Changes

- Added optional `train_number` field to `TrainMainTransferForm` (stored in `type_specific_data`)
- Added `train_status_redirect` view: resolves specific train status or station departure board via viaggiatreno API
- Added train status button in transfer detail cards (active only on travel day)
- Added static Trainline/Trenitalia search buttons in form (open in new tab)
- Added IT translations for new labels
- Removed unused `carriage` and `seat` properties from `MainTransfer` model
- Updated documentation (EN + IT)
- 100% test coverage maintained (721 tests)
