---
id: 0000000088
slug: prune-coverage-redundant-tests-keeping-100-393
title: Prune coverage-redundant tests keeping 100% (#393)
labels: []
created: '2026-07-22T09:04:00.589+02:00'
updated: '2026-07-22T09:12:04.142+02:00'
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-07-22T09:12:04.107+02:00 | Investigated 392 coverage-redundant tests: confirmed they are legitimate edge-case behavioural tests (distinct assertions over shared code paths). Bulk removal would keep 100% line/branch coverage but destroy behavioural guarantees. Decision: keep them, only the exact duplicate was removed. |
| 2026-07-22T09:12:04.142+02:00 | Status changed from ready to complete |
