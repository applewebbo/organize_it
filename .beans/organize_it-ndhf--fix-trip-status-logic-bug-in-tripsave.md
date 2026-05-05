---
# organize_it-ndhf
title: Fix trip status logic bug in Trip.save()
status: todo
type: bug
created_at: 2026-05-03T06:45:54Z
updated_at: 2026-05-03T06:45:54Z
---

Last elif in Trip.save() uses 'self.start_date <= seven_days_after' which never sets NOT_STARTED for trips starting >7 days away. Should be 'else: self.status = 1'.
