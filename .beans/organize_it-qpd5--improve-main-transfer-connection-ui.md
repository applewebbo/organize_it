---
# organize_it-qpd5
title: Improve main transfer connection UI
status: in-progress
type: feature
created_at: 2026-01-25T15:10:43Z
updated_at: 2026-01-25T15:10:43Z
---

Modify the UI of transfers shown in arrival and departure sections:

1. Replace green badge with transfer icon in connection display - show transport mode icon instead
2. Update 'Add connection' button to match edit/delete button styling:
   - Align to right
   - Icon only on mobile
   - Icon + text on sm+ screens

Files to modify:
- templates/trips/includes/main-transfers.html (lines 89-91 for connection display, lines 104-111 and 209-216 for add button)
