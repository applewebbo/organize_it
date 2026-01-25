---
# organize_it-el8f
title: Add transfer from main transfer arrival to first event/stay
status: completed
type: feature
priority: normal
created_at: 2026-01-25T06:50:52Z
updated_at: 2026-01-25T15:04:56Z
---

Add the ability to add a transfer from main transfer arrival/departure location to first/last event or stay.

## Context
After arriving via main transfer (e.g., flight), users need to get to their first destination (first event or first stay). Similarly, before departure they need to get from their last location to the departure point. This feature adds a quick way to create these connecting transfers.

## Implementation approach
Using a single model `MainTransferConnection` that works for both ARRIVAL and DEPARTURE:
- For ARRIVAL: main_transfer → event/stay (first day)
- For DEPARTURE: event/stay (last day) → main_transfer
- OneToOne relationship ensures max 1 connection per main transfer

## Checklist
- [x] Create MainTransferConnection model with event/stay foreign keys
- [x] Create and run migration
- [x] Add create/edit/delete views and forms
- [x] Create modal templates for selecting event/stay destination
- [x] Update main-transfers.html to show connection status and add/edit buttons
- [x] Add URL patterns
- [x] Add tests for model and views
- [x] Update bean checklist as completed

Related to #230
