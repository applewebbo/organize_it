---
# organize_it-jqqy
title: Move Mapbox geocoding to background task
status: scrapped
type: task
priority: normal
created_at: 2026-05-10T11:32:01Z
updated_at: 2026-05-10T11:32:40Z
---

Codeberg issue #305. Move synchronous geocoding from Stay/Event/MainTransfer.save() to async django-q2 tasks using post_save + transaction.on_commit.
