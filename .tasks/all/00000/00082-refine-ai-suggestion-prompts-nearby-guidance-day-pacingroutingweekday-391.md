---
id: 0000000082
slug: refine-ai-suggestion-prompts-nearby-guidance-day-pacingroutingweekday-391
title: >-
  Refine AI suggestion prompts: nearby guidance + day pacing/routing/weekday
  (#391)
labels: []
created: '2026-07-21T15:22:03.142+02:00'
updated: '2026-07-21T15:22:19.988+02:00'
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-07-21T15:22:19.951+02:00 | Prompt-only changes in suggestions/prompts.py, TDD. Added nearby radius line (build_prompt), day pacing (4-6 stops), route anti-backtracking, weekday awareness (_WEEKDAYS). 4 new tests in tests/suggestions/test_prompts.py. Verified e2e with probe_day_itinerary on Milano trip 198 (nearby: 5 stops clustered; day_trips: Como 6 stops clustered). |
| 2026-07-21T15:22:19.988+02:00 | Status changed from ready to complete |
