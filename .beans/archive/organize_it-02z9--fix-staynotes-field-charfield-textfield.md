---
# organize_it-02z9
title: 'Fix Stay.notes field: CharField -> TextField'
status: completed
type: bug
priority: normal
created_at: 2026-05-03T06:45:54Z
updated_at: 2026-05-10T11:44:19Z
---

Stay.notes is CharField(max_length=500) which is too limiting for accommodation notes. Change to TextField(blank=True) and add migration.

## Summary of Changes\n\nCambiato notes da CharField(max_length=500) a TextField(blank=True) su Stay ed Event. Migrazione 0026. Test aggiornati per usare campo vuoto come caso invalido invece di stringa lunga.
