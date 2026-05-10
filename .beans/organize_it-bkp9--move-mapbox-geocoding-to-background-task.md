---
# organize_it-bkp9
title: Move Mapbox geocoding to background task
status: todo
type: task
created_at: 2026-05-10T11:32:06Z
updated_at: 2026-05-10T11:32:06Z
---

Codeberg issue #305. Move synchronous geocoding from Stay/Event/MainTransfer.save() to async django-q2 tasks using post_save + transaction.on_commit.
