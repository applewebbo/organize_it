---
# organize_it-gzjd
title: Trip-detail grouping by consecutive destination
status: in-progress
type: task
priority: normal
created_at: 2026-05-06T16:31:48Z
updated_at: 2026-05-07T05:52:59Z
parent: organize_it-h7o7
---

In trip-detail view, detect if all days share the same destination (or are all blank): if yes, keep current layout. If at least one differs, group days into consecutive destination blocks and render with section headers. Grouping is by consecutive run, not global uniqueness.
