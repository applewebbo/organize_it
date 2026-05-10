---
# organize_it-45ie
title: 'Improve event list item UI: fix title alignment and move notes to edit modal'
status: completed
type: feature
priority: normal
created_at: 2026-04-30T06:00:42Z
updated_at: 2026-05-10T10:51:45Z
---

Issue: #288

- [ ] Fix vertical alignment of event title vs icon in event_list_item (items-center missing or icon not aligned).
2. Remove the notes button (paperclip) from both event.html and event_list_item.html.
3. Remove the notes badge logic (bg-slate-400 dot) from both templates.
4. Add a '+ Note' button inside the event-modify modal (or event-detail modal) that loads note create/edit inline.
5. In event-detail modal, show existing notes directly (no badge needed).

## Summary of Changes

- Aggiunto `shrink-0` e `leading-tight` al titolo evento in `event_list_item.html` per allineamento verticale
- Rimosso bottone note (paperclip) e badge da `event_list_item.html` e `event.html`
- Aggiunto bottone Notes in `event-detail.html`: icona ph-note su mobile, testo 'Notes' su sm+
- Note visualizzate direttamente in `experience-detail.html` e `meal-detail.html` se presenti
