---
# organize_it-02z9
title: 'Fix Stay.notes field: CharField -> TextField'
status: todo
type: bug
created_at: 2026-05-03T06:45:54Z
updated_at: 2026-05-03T06:45:54Z
---

Stay.notes is CharField(max_length=500) which is too limiting for accommodation notes. Change to TextField(blank=True) and add migration.
