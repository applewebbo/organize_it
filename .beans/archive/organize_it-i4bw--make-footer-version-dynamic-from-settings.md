---
# organize_it-i4bw
title: Make footer version dynamic from settings
status: completed
type: task
priority: normal
created_at: 2026-03-05T14:09:37Z
updated_at: 2026-03-05T14:14:38Z
---

Add APP_VERSION to core/settings.py and use it in the footer template via a context processor, so the version is defined in a single place. Also align pyproject.toml version with the release version.

## Changes needed
- [x] Add APP_VERSION = "2026.3.2" to core/settings.py
- [x] Create a context processor that exposes APP_VERSION to all templates
- [x] Update footer.html to use {{ APP_VERSION }} instead of hardcoded string
- [x] Update pyproject.toml version to match release version
- [x] Register the context processor in TEMPLATES settings

## Codeberg Issue
#233

## Summary of Changes

- Added APP_VERSION = "2026.3.2" to core/settings.py
- Created core/context_processors.py with app_version context processor
- Registered context processor in TEMPLATES settings
- Updated footer.html to use {{ APP_VERSION }}
- Updated pyproject.toml version from 0.3.0 to 2026.3.2
- Added test in tests/test_context_processors.py
