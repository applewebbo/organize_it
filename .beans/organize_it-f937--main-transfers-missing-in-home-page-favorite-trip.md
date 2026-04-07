---
# organize_it-f937
title: Main transfers missing in home page favorite trip
status: completed
type: bug
priority: normal
created_at: 2026-04-07T18:20:00Z
updated_at: 2026-04-07T18:33:13Z
---

Main transfers not shown in the home page favorite trip card for authenticated users (issue #264)

## Summary of Changes\n\n- Moved _get_flight_origin_icao to utils.py as get_flight_origin_icao\n- get_trips() now extracts arrival_transfer/departure_transfer from prefetched main_transfers\n- Adds arrival_transfer, departure_transfer, both_transfers_exist, arrival_origin_icao, departure_origin_icao to home page context\n- 3 new tests, 100% coverage
