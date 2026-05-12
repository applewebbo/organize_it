---
# organize_it-vv6s
title: Refactor trips/views.py into multiple focused modules
status: draft
type: task
priority: normal
created_at: 2026-05-12T13:36:11Z
updated_at: 2026-05-12T13:36:39Z
---

trips/views.py has grown to 3337 lines and should be split into focused modules by domain (e.g. trip views, day views, event views, transfer views, map views, etc.) to improve maintainability and navigability. All imports and URL routing must remain compatible.

Codeberg issue: #313
