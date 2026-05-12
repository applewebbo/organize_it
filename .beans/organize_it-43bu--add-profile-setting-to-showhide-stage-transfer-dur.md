---
# organize_it-43bu
title: Add profile setting to show/hide stage transfer duration/distance info
status: completed
type: feature
priority: normal
created_at: 2026-05-09T13:27:05Z
updated_at: 2026-05-12T13:37:45Z
---

Add a boolean field to the Profile model (show_transfer_info, default True) to allow users to toggle the visibility of transfer duration/distance info between trip stages. The setting is global (applies to all trips) and is configured in the existing profile settings page.

## Scope extension\n\nAdded also:\n-  field to Profile: if False, weather API is not called in background task\n- Both fields in Display Preferences section of profile settings\n- issue #310 covers both settings

## Summary of Changes\n\n- Added  and  BooleanField to Profile (migration 0008)\n- Both fields in Display Preferences section of profile settings\n- : nasconde il widget transfer-info nei template; l'endpoint HTMX restituisce 204 se disabilitato\n- : nasconde i widget meteo (widget giornaliero + summary header + mappa); il task background esclude i trip di utenti con preferenza disabilitata\n- Test aggiunto per il caso 204 dell'endpoint transfer_info\n- Copertura al 100%
