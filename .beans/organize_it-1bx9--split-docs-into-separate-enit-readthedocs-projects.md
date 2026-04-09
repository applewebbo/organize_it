---
# organize_it-1bx9
title: Split docs into separate EN/IT ReadTheDocs projects
status: completed
type: task
priority: normal
created_at: 2026-04-09T06:55:24Z
updated_at: 2026-04-09T06:58:36Z
---

Create mkdocs-it.yml for Italian docs, new RTD project organize-it-ita, second Codeberg webhook, language-aware links in app, remove broken language switcher. Issue #269.

## Summary of Changes\n\n- Split mkdocs.yml (EN only, docs_dir: docs/en) and mkdocs-it.yml (IT only, docs_dir: docs/it)\n- Added .readthedocs-it.yaml for the organize-it-ita RTD project\n- Updated quick_guide.html doc link to be language-aware (IT → organize-it-ita.readthedocs.io)\n- Removed mkdocs-static-i18n from docs/requirements.txt\n\nManual steps remaining: create RTD project organize-it-ita + Codeberg webhook.
