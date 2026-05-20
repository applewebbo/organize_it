---
id: '0000000005'
slug: handle-trips-without-dates-draft-status
title: Handle trips without dates (draft status)
labels:
  - feature
created: '2026-05-20T07:44:13.117+02:00'
updated: '2026-05-20T07:44:13.117+02:00'
---

## Description

Trips without start_date/end_date never update status. Add explicit DRAFT status or handle None dates gracefully in Trip.save() status logic.
---

## Task Comments

| Commented At | Comment |
| --- | --- |
