---
# organize_it-a3nk
title: Redesign SimpleTransfer display in day list view
status: completed
type: feature
priority: normal
created_at: 2026-01-14T06:48:04Z
updated_at: 2026-01-14T07:04:49Z
---

Modify the SimpleTransfer visualization within the event list view:

## Requirements
1. Position the SimpleTransfer at the bottom of the event card
2. Add a background that indicates the transport mode (car, walking, transit, bicycling)
3. Show an arrow pointing to the destination event name
4. Add two buttons:
   - **Map**: link to Google Maps with the route
   - **Delete**: delete the transfer

## Checklist
- [ ] Read the current template structure in day-list-content.html
- [ ] Design transport mode background colors/icons
- [ ] Update the SimpleTransfer display section in the template
- [ ] Add Google Maps link button using the existing google_maps_url property
- [ ] Add delete button with HTMX
- [ ] Test the new UI visually
