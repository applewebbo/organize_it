---
# organize_it-ndhf
title: Fix trip status logic bug in Trip.save()
status: completed
type: bug
priority: normal
created_at: 2026-05-03T06:45:54Z
updated_at: 2026-05-10T11:44:19Z
---

Last elif in Trip.save() uses 'self.start_date <= seven_days_after' which never sets NOT_STARTED for trips starting >7 days away. Should be 'else: self.status = 1'.

## Summary of Changes\n\nSostituito l'elif con else nel Trip.save() per impostare correttamente lo status NOT_STARTED per i viaggi con start_date > 7 giorni da oggi.
