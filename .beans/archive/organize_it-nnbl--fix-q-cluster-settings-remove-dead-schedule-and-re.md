---
# organize_it-nnbl
title: 'Fix Q_CLUSTER settings: remove dead schedule and redis config'
status: completed
type: task
priority: normal
created_at: 2026-03-05T08:12:02Z
updated_at: 2026-03-05T13:57:27Z
---

The Q_CLUSTER settings have two issues to fix:

1. **Dead code**: the `schedule` key in Q_CLUSTER is not a django-q2 feature - the library never reads it. Schedules must be created via data migration or admin.
2. **Incorrect redis config**: production Q_CLUSTER has both `orm` and `redis` keys, but there is no Redis container for organize-it (only srv-captain--school-menu-redis exists). Remove the redis block.

## Changes needed
- [x] Remove `schedule` block from Q_CLUSTER in both dev and prod settings (core/settings.py)
- [x] Remove `redis` block from production Q_CLUSTER (core/settings.py)
- [x] Add a data migration to auto-create the Schedule objects in the DB

## Codeberg Issue\n\n#232

## Summary of Changes\n\n- Removed dead `schedule` key from Q_CLUSTER in dev and prod (django-q2 ignores it)\n- Removed `redis` block from production Q_CLUSTER (no Redis container for organize-it)\n- Added data migration `0007_create_django_q_schedules` that auto-creates the 3 Schedule objects via `get_or_create` (idempotent)
