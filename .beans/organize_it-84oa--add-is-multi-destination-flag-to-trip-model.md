---
# organize_it-84oa
title: Add is_multi_destination flag to Trip model
status: todo
type: task
created_at: 2026-05-07T06:45:25Z
updated_at: 2026-05-07T06:45:25Z
parent: organize_it-h7o7
---

Add boolean field Trip.is_multi_destination (default False). When True: show destinations modal button, enable grouping in trip-detail, show destination field per day. When False: hide all multi-destination UI, keep current single-destination layout. Add field to trip create/edit forms.
