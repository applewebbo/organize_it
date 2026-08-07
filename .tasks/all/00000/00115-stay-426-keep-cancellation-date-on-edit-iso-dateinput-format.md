---
id: '0000000115'
slug: stay-426-keep-cancellation-date-on-edit-iso-dateinput-format
title: 'Stay #426: keep cancellation date on edit (ISO DateInput format)'
labels: []
created: '2026-08-07T09:03:36.290+02:00'
updated: '2026-08-07T09:03:48.838+02:00'
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-08-07T09:03:48.801+02:00 | StayForm was the only DateInput in the project missing format='%Y-%m-%d'; under the it locale Django rendered 19/08/2026, which <input type="date"> discards, so any save wiped the stored date. Regression test pins the rendering under translation.override('it') since the en locale would pass either way. |
| 2026-08-07T09:03:48.838+02:00 | Status changed from ready to complete |
