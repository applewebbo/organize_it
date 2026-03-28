---
# organize_it-bp29
title: Fix cloudinary storage backend missing in production
status: completed
type: bug
priority: normal
created_at: 2026-03-28T12:42:36Z
updated_at: 2026-03-28T13:25:48Z
---

django-storages installed without [cloudinary] extra, causing InvalidStorageError in prod. Fix: change to django-storages[cloudinary] in pyproject.toml

## Summary of Changes

- Replaced `django-storages[cloudinary]` (backend didn't exist) with `django-cloudinary-storage>=0.3.0`
- Added `cloudinary_storage` to INSTALLED_APPS
- Added `CLOUDINARY_STORAGE` config in production settings reading `CLOUDINARY_URL` from env
- Changed storage backend to `cloudinary_storage.storage.MediaCloudinaryStorage`
