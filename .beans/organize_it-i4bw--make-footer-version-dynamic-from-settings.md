---
# organize_it-i4bw
title: Make footer version dynamic from settings
status: in-progress
type: task
created_at: 2026-03-05T14:09:37Z
updated_at: 2026-03-05T14:09:37Z
---

Add APP_VERSION to core/settings.py and use it in the footer template via a context processor, so the version is defined in a single place. Also align pyproject.toml version with the release version.

## Changes needed
- [ ] Add APP_VERSION = "2026.3.2" to core/settings.py
- [ ] Create a context processor that exposes APP_VERSION to all templates
- [ ] Update footer.html to use {{ APP_VERSION }} instead of hardcoded string
- [ ] Update pyproject.toml version to match release version
- [ ] Register the context processor in TEMPLATES settings

## Codeberg Issue
#233
