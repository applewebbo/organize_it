---
# organize_it-lbjv
title: Cache Google Places API
status: scrapped
type: task
priority: normal
created_at: 2026-03-30T15:08:36Z
updated_at: 2026-03-30T18:16:49Z
---

Add 24h caching to Google Places enrichment API calls. Codeberg issue: #257

## Reasons for Scrapping

Marginal benefit: enrich calls are on-demand (user-triggered), not in automatic loops. The real gain would only apply if two users enrich the same place within 24h. Adds code complexity and test overhead for minimal performance improvement. Skipped in favor of higher-impact optimizations.
