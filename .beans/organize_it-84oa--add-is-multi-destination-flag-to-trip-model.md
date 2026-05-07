---
# organize_it-84oa
title: Add is_multi_destination flag to Trip model
status: scrapped
type: task
priority: normal
created_at: 2026-05-07T06:45:25Z
updated_at: 2026-05-07T07:13:06Z
parent: organize_it-h7o7
---

Add boolean field Trip.is_multi_destination (default False). When True: show destinations modal button, enable grouping in trip-detail, show destination field per day. When False: hide all multi-destination UI, keep current single-destination layout. Add field to trip create/edit forms.

## Reasons for Scrapping\n\nNon più necessario: lo stato multi-destinazione emerge naturalmente dall'esistenza di tappe personalizzate (Day.destination != trip.destination). Il bottone per gestire le tappe è stato spostato nell'header del trip, non nella sezione 'Things to Do'.
