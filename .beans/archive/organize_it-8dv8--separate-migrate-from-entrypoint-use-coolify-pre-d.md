---
# organize_it-8dv8
title: Separate migrate from entrypoint — use Coolify pre-deploy command
status: scrapped
type: task
priority: normal
created_at: 2026-05-03T06:36:49Z
updated_at: 2026-05-13T05:56:26Z
---

Move migrate/compilemessages/collectstatic to Coolify pre-deploy command so migrations run before traffic switches to new container. Leave only hivemind start in entrypoint.sh.

## Analysis\n\nOnly  is safe to move to Coolify pre-deploy because it operates on the external shared database. All other commands generate filesystem artifacts that would be lost in the temporary pre-deploy container:\n\n-  → produces .mo files inside the container\n-  → produces compiled CSS inside the container\n-  → copies static files inside the container\n\nThese must stay in entrypoint.sh (or be moved to the Docker build step). The bean as described would break static files and translations in production.

## Reasons for Scrapping\n\nThe original premise was flawed. Only migrate operates on external state (DB), but even that has risks if the new container fails to start post-migration. All other commands (compilemessages, tailwind build, collectstatic) generate filesystem artifacts that are lost in the temporary pre-deploy container. The current entrypoint.sh approach is correct.
