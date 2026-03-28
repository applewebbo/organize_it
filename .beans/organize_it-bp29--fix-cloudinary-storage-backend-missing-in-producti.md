---
# organize_it-bp29
title: Fix cloudinary storage backend missing in production
status: in-progress
type: bug
created_at: 2026-03-28T12:42:36Z
updated_at: 2026-03-28T12:42:36Z
---

django-storages installed without [cloudinary] extra, causing InvalidStorageError in prod. Fix: change to django-storages[cloudinary] in pyproject.toml
