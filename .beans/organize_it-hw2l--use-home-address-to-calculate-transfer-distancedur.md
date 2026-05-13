---
# organize_it-hw2l
title: Use home address to calculate transfer distance/duration for first/last trip day
status: completed
type: feature
priority: normal
created_at: 2026-05-09T13:27:00Z
updated_at: 2026-05-13T07:06:32Z
---

If no main transfer is present, use the trip creator's home address (Profile.home_address_latitude/longitude) to calculate transfer duration/distance to the first day of the trip (and from the last day). If home address is missing, skip silently.

## Todo\n\n- [x] Add transfer_to_home_duration / transfer_to_home_distance fields to Day model\n- [x] Create migration\n- [x] Modify calculate_day_transfer: day 1 → use home as origin if no ARRIVAL MainTransfer\n- [x] Add calculate_to_home logic for last day (no DEPARTURE MainTransfer)\n- [x] Update group_days_by_destination to expose home transfer data\n- [x] Update template to show home transfers\n- [x] Add profile signal to recalculate when home_address changes\n- [x] Write tests (TDD)
