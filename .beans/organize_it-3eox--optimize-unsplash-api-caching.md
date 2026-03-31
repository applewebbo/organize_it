---
# organize_it-3eox
title: Optimize Unsplash API caching
status: scrapped
type: task
priority: normal
created_at: 2026-03-30T15:08:36Z
updated_at: 2026-03-31T05:47:53Z
---

Extend Unsplash cache from 6h to 24h, cache download URL. Codeberg issue: #260

## Reasons for Scrapping

On-demand call (user-triggered UI search), not a loop. Download happens once per trip (image saved to model). Rate limit of 50 req/h is hard to hit with normal usage. Extending 6h→24h risks showing removed photos (copyright takedowns). Zero meaningful benefit.
