---
id: '0000000030'
slug: daily-digest-email-issue-346
title: 'Daily digest email (issue #346)'
labels: []
created: '2026-06-12T16:55:00.993+02:00'
updated: '2026-06-12T17:28:21.329+02:00'
---

## Description

Implement daily 'today on your trip' email task for issue #346: model fields, task, templates, schedule, tests, docs
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-06-12T16:55:05.825+02:00 | Status changed from ready to in-progress |
| 2026-06-12T17:22:17.967+02:00 | Implemented: model fields (Profile.notify_daily_digest, Trip.daily_digest_sent_on), tasks (send_daily_digests + helpers), email templates (subject/txt/html), schedule migration (cron 07:00), profile form/template exposure, IT translations, docs in EN/IT weather pages. 15 new tests, full suite 1268 passing. |
| 2026-06-12T17:28:21.329+02:00 | Status changed from in-progress to complete |
