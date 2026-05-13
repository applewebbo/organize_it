---
# organize_it-mnvo
title: 'Fix CI: pin Python 3.14 in .python-version'
status: completed
type: bug
priority: normal
created_at: 2026-05-13T05:50:03Z
updated_at: 2026-05-13T05:50:26Z
---

CI fails with 'No interpreter found for Python 3.14.4'. Pin to 3.14 to use whatever patch version is in the uv Docker image.

## Summary of Changes\n\nModified .python-version from 3.14.4 to 3.14 so uv uses whatever 3.14.x patch version is bundled in the CI Docker image.
