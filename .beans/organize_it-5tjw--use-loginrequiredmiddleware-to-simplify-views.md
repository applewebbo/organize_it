---
# organize_it-5tjw
title: Use LoginRequiredMiddleware to simplify views
status: completed
type: task
priority: normal
created_at: 2026-04-28T13:33:10Z
updated_at: 2026-04-28T13:39:56Z
---

Issue #286: add LoginRequiredMiddleware, remove @login_required, add @login_not_required to public views

## Summary of Changes\n\nAggiunto LoginRequiredMiddleware in settings.py. Rimossi 79 @login_required da trips/views.py e accounts/views.py. Aggiunti @login_not_required a home, shared_trip_detail, accept_invitation. Test aggiornati con pattern with self.login(user).
