---
# organize_it-5lb8
title: Cloudinary storage for media files in production
status: completed
type: feature
priority: normal
created_at: 2026-03-26T12:27:51Z
updated_at: 2026-03-26T12:31:29Z
---

Switch from FileSystemStorage to Cloudinary via django-storages for persistent media storage in production. Fixes media files lost on Coolify redeploy. Fix #248

## Summary of Changes\n\n- Added  1.44.1 package\n- Replaced  with  in production STORAGES config\n- Files organized under  folder prefix on Cloudinary\n- Dev/test environments unchanged (still use FileSystemStorage)\n- No changes to urls.py needed: static() handles dev, Cloudinary CDN handles prod
