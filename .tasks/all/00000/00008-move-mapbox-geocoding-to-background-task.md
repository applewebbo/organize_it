---
id: 0000000008
slug: move-mapbox-geocoding-to-background-task
title: Move Mapbox geocoding to background task
labels:
  - task
created: '2026-05-20T07:44:13.223+02:00'
updated: '2026-05-20T07:44:13.223+02:00'
---

## Description

Codeberg issue #305. Move synchronous geocoding from Stay/Event/MainTransfer.save() to async django-q2 tasks using post_save + transaction.on_commit.
---

## Task Comments

| Commented At | Comment |
| --- | --- |
