---
# organize_it-8dv8
title: Separate migrate from entrypoint — use Coolify pre-deploy command
status: todo
type: task
created_at: 2026-05-03T06:36:49Z
updated_at: 2026-05-03T06:36:49Z
---

Move migrate/compilemessages/collectstatic to Coolify pre-deploy command so migrations run before traffic switches to new container. Leave only hivemind start in entrypoint.sh.
