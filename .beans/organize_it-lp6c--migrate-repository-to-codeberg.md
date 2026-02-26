---
# organize_it-lp6c
title: Migrate repository to Codeberg
status: in-progress
type: task
created_at: 2026-02-26T14:25:09Z
updated_at: 2026-02-26T14:25:09Z
---

Migrate organize_it from GitHub to Codeberg (ssh://git@codeberg.org/webbografico/organize_it.git).

## Changes needed
- [ ] Update git remote to Codeberg
- [ ] Create .woodpecker.yml (Woodpecker CI, with MAPBOX_ACCESS_TOKEN secret)
- [ ] Remove GitHub Actions workflow (.github/workflows/tests.yaml)
- [ ] Add bin/codeberg CLI script (from trantrac)
- [ ] Add Codeberg section to justfile (issues + releases commands)
- [ ] Add CODEBERG_API_TOKEN to .env.example
- [ ] Update .claude/settings.local.json permissions
