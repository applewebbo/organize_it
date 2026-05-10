---
# organize_it-41bd
title: Fix language selector background in light theme
status: completed
type: bug
created_at: 2026-05-10T10:55:20Z
updated_at: 2026-05-10T10:55:20Z
---

Language chooser dropdown used raw Tailwind dark: classes (bg-slate-700) causing dark background on light theme. Fixed by using DaisyUI bg-base-200/text-base-content classes.
