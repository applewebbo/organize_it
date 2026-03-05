---
# organize_it-lp6c
title: Migrate repository to Codeberg
status: completed
type: task
priority: normal
created_at: 2026-02-26T14:25:09Z
updated_at: 2026-02-26T14:32:25Z
---

Migrate organize_it from GitHub to Codeberg (ssh://git@codeberg.org/webbografico/organize_it.git).

## Changes needed
- [x] Update git remote to Codeberg
- [x] Create .woodpecker.yml (Woodpecker CI, with MAPBOX_ACCESS_TOKEN secret)
- [x] Remove GitHub Actions workflow (.github/workflows/tests.yaml)
- [x] Add bin/codeberg CLI script (from trantrac)
- [x] Add Codeberg section to justfile (issues + releases commands)
- [x] Add CODEBERG_API_TOKEN to .env.example
- [x] Update .claude/settings.local.json permissions

## Summary of Changes

- Updated git remote to ssh://git@codeberg.org/webbografico/organize_it.git
- Replaced GitHub Actions with Woodpecker CI (.woodpecker.yml)
- Added bin/codeberg CLI script (auto-detects repo from remote URL)
- Added Codeberg issues/releases section to justfile
- Added CODEBERG_API_TOKEN to .env.example
- Added SKILLS.md with Claude skills documentation
- Updated .claude/settings.local.json with beans permissions
- Created Codeberg issue #231 and committed (143ccd0)
