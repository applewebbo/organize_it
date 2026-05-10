---
# organize_it-kwe2
title: 'Refactor transfer duration/distance: rename fields, new semantics, UI improvements'
status: completed
type: task
priority: normal
created_at: 2026-05-09T06:02:19Z
updated_at: 2026-05-09T06:36:30Z
---

## Summary of Changes

- Renamed Day.transfer_duration_to_next → transfer_duration_from_prev and transfer_distance_to_next → transfer_distance_from_prev (migration 0024)
- Changed calculate_day_transfer semantics: now takes first day of arriving stage, looks at number-1 for origin
- Updated group_days_by_destination to read from first_day of next group
- Simplified create_stage: 2 async_task calls instead of N+2
- Simplified delete_stage: immediate sync reset + 1 async for next stage
- city-results.html aligned to address-results.html pattern with + icon
- trip-create form: Nominatim search full-width, help text, no blocking
- All tests updated and 100% coverage
