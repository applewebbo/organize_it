---
# organize_it-wvkk
title: Hide simple transfer button when no next event
status: completed
type: bug
priority: normal
created_at: 2026-01-25T06:50:47Z
updated_at: 2026-01-25T07:02:16Z
---

Don't show button to add simple transfer instead of showing an error message when no next event is present.

## Context
Currently, when there is no next event, clicking the 'add simple transfer' button shows an error message. Instead, the button should not be displayed at all.

## Checklist
- [x] Find where the simple transfer button is rendered
- [x] Add condition to hide button when no next event exists
- [x] Add/update tests

Related to #230
