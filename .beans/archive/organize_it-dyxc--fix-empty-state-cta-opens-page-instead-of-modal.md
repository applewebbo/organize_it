---
# organize_it-dyxc
title: Fix empty state CTA opens page instead of modal
status: completed
type: bug
priority: normal
created_at: 2026-03-18T14:08:43Z
updated_at: 2026-03-18T14:20:49Z
---

The 'Create Your First Trip' button in empty_state.html uses a plain <a href> link instead of the HTMX+Alpine.js modal pattern used elsewhere. Should use hx-get, hx-target='#dialog', hx-swap='innerHTML' and dispatch 'open-modal'.

## Summary of Changes\n\nReplaced plain anchor tag with HTMX button (hx-get, hx-target='#dialog', hx-swap='innerHTML') and Alpine.js dispatch. Tracked as Codeberg issue #235.
