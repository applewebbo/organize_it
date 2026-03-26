---
# organize_it-admt
title: Add FlightAware flight status links to flight transfers
status: completed
type: feature
priority: normal
created_at: 2026-03-24T07:06:44Z
updated_at: 2026-03-24T08:08:57Z
---

Issue #245: enrich airports CSV with ICAO codes via OurAirports, add flight status button in transfer detail card (FlightAware deep link), active only on travel day. If flight_number set → /live/flight/AZ1234, else → /live/airport/LIMC (hidden if no ICAO).

## Summary of Changes

- Enriched airports_simple.csv with ICAO codes via OurAirports (5724/7698 airports)
- Added one-shot management command enrich_airports_icao (excluded from coverage)
- Added flight_status_redirect view: flight_number → /live/flight/AZ1234; ICAO → /live/airport/LIMC; fallback → flightaware.com
- Added flight status button in transfer detail cards (active only on travel day AND when flight_number or ICAO available)
- Simplified FlightMainTransferForm: removed company, company_website, booking_reference, ticket_url
- Added IT translations (Stato volo, Partenze dall'aeroporto)
- Updated trip_detail view context with today, arrival_origin_icao, departure_origin_icao
- 100% test coverage maintained (727 tests)
