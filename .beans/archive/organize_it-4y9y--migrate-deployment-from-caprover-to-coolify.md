---
# organize_it-4y9y
title: Migrate deployment from CapRover to Coolify
status: completed
type: task
priority: normal
created_at: 2026-03-17T06:37:03Z
updated_at: 2026-03-17T06:54:05Z
---

- [x] Remove captain-definition (CapRover specific)
- [x] Update justfile removing CapRover references
- [x] Provide Coolify configuration instructions (webhook Codeberg, healthcheck via UI)

## Summary of Changes

- Removed `captain-definition` (CapRover-specific file)
- Updated `justfile` docker-test comment from CapRover to Coolify
