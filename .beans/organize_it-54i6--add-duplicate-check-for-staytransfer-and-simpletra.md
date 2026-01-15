---
# organize_it-54i6
title: Add duplicate check for StayTransfer and SimpleTransfer creation
status: completed
type: bug
priority: normal
created_at: 2026-01-15T14:29:12Z
updated_at: 2026-01-15T14:35:41Z
---

## Problem
When creating a StayTransfer, if one already exists for the same stays, a database IntegrityError occurs (UNIQUE constraint failed).

## Solution
Fixed the form validation in `StayTransferCreateForm` and `SimpleTransferCreateForm` to use explicit database queries instead of `hasattr()`. The original validation used Django's reverse relation accessor which returned the in-memory instance instead of querying the database, causing the validation to incorrectly pass.

## Checklist
- [x] Add duplicate check in StayTransferCreateForm (trips/forms.py:2403-2420)
- [x] Check if SimpleTransfer has the same issue - YES, same bug
- [x] Add duplicate check in SimpleTransferCreateForm (trips/forms.py:2255-2272)
- [x] Run tests to verify - 582 tests pass
