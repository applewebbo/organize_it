---
# organize_it-r9g9
title: Add manual weather refresh view and fetch status visibility
status: todo
type: feature
created_at: 2026-05-03T06:45:54Z
updated_at: 2026-05-03T06:45:54Z
---

Weather data/fetch infrastructure exists (weather.py, tasks, templates, Day.weather_data) but no URL/view to trigger manual refresh. Add a view to force-fetch weather and show last fetch time/errors in the day header.
