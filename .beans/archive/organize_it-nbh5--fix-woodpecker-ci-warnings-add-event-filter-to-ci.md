---
# organize_it-nbh5
title: 'Fix Woodpecker CI warnings: add event filter to CI steps'
status: completed
type: bug
priority: normal
created_at: 2026-05-14T06:53:40Z
updated_at: 2026-05-14T06:55:13Z
---

Woodpecker CI reports bad_habit warnings for steps.test and steps.deploy-docs missing a 'when' block with event filter. Add appropriate when blocks. Ref: Codeberg issue #316.

## Summary of Changes\n\nAdded `event: push` to the global `when` block in `.woodpecker.yml`. Resolves bad_habit warnings for both steps.test and steps.deploy-docs that were missing an event filter.
