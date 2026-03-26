---
# organize_it-xpdo
title: Add Trainline deep link and simplify train transfer form
status: completed
type: feature
priority: normal
created_at: 2026-03-23T09:25:46Z
updated_at: 2026-03-23T10:17:14Z
---

Issue #244: Trainline deep link for train transfers, simplify form removing train number/operator/booking ref/ticket URL, stations on same row sm+

## Summary of Changes
- Removed fields from TrainMainTransferForm: train_number, company, company_website, booking_reference, ticket_url, carriage, seat
- Station fields (origin/destination) now on same row on sm+ screens (grid 2 cols)
- Added 'Search on Trainline' and 'Search on Trenitalia' buttons in train form (open in new tab, stacked on mobile, side-by-side on sm+)
- Added IT translation 'Cerca su'
- Updated all affected tests to 100% coverage
