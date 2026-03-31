---
# organize_it-prgp
title: Optimize session cleanup task
status: completed
type: task
priority: normal
created_at: 2026-03-30T15:08:36Z
updated_at: 2026-03-31T05:44:49Z
---

Use single queryset for count+delete in cleanup_old_sessions(). Codeberg issue: #259

## Summary of Changes

Replaced double queryset (count + delete) with single delete() call.
Django's delete() returns (N, {model: N}) — count extracted directly.
2 DB queries → 1 DB query.
