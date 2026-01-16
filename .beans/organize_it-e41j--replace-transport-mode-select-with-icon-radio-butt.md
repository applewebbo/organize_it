---
# organize_it-e41j
title: Replace transport_mode select with icon radio buttons
status: in-progress
type: feature
created_at: 2026-01-15T14:43:52Z
updated_at: 2026-01-15T14:43:52Z
---

## Description
Replace the transport_mode select dropdown with 4 radio buttons featuring Phosphor icons.

## Requirements
- 4 radio buttons with Phosphor icons (car, walking, bicycle, train)
- Icons slightly larger than default
- Layout: 2x2 grid on mobile, 4 in a row on sm+
- Style similar to avatar selection in profile settings

## Checklist
- [ ] Create TransportModeRadioSelect widget in trips/widgets.py
- [ ] Apply widget to SimpleTransferCreateForm
- [ ] Apply widget to StayTransferCreateForm
- [ ] Test on mobile and desktop
