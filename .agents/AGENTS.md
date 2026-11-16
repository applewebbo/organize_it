# organize_it — Project Context

## Overview
Django web app for organizing trips and travel plans. Stack: Django 6.0+, Python 3.14+, Tailwind/daisyUI, HTMX, Alpine.js, django-cotton components.

## Stack
| Layer | Choice |
|-------|--------|
| Backend | Django 6.0+, Python 3.14+ |
| DB | SQLite (dev), PostgreSQL (prod) |
| Frontend | TailwindCSS + daisyUI, HTMX, Alpine.js, django-cotton |
| Auth | django-allauth (email-based, no username) |
| Tasks | django-q2 (ORM dev, Redis prod, sync in tests) |
| Maps | Mapbox (geocoding), Folium (rendering) |
| Images | Pillow + Unsplash API |

## Commands
```bash
just install      # uv sync
just local        # dev server + Tailwind
just serve        # web + q2 worker (mprocs) ← recommended
just ftest        # run tests in parallel (8 workers) ← always use this
just cov          # coverage (must be 100%)
just lint         # ALWAYS before git add
just migrate / just makemigrations
just docs-serve / just docs-build
```

## Testing rules (project-specific)
- The full suite is slow. **Always run specific tests first**: `just ftest <path/to/test>`
- Full suite: `just ftest` only after specific tests pass

## Architecture
- **All views are FBV** (function-based). No CBV unless strictly needed.
- HTMX views check `request.htmx`, return fragments via `#fragment` syntax
- Mutations typically return `HttpResponse(status=204, headers={"HX-Trigger": "..."})`
- Use `prefetch_related` / `select_related` to avoid N+1

## Core Model Relationships
- `Trip` → (many) `Day` → (many) `Event` (Experience or Meal via STI)
- `Day` → (0-1) `Stay` (a Stay can span multiple Days)
- `Trip` → (many) `Link`
- `MainTransfer` / `MainTransferConnection` for arrival/departure

## Key Behaviors
- Trip status auto-updates from dates (NOT_STARTED → IMPENDING → IN_PROGRESS → COMPLETED → ARCHIVED)
- Days auto-generate via `update_trip_days` signal when trip dates change
- Location models (Event, Stay) auto-geocode on save using Mapbox
- STI: `Experience` and `Meal` extend `Event`; `category` auto-set in `save()`

## Templates
- Base: `templates/base.html`
- Cotton components: `templates/cotton/`
- App templates: `templates/trips/`
- Template fragments via `#fragment` for HTMX partial rendering

## Tests
- Located in `tests/` (not in app dirs)
- Factories via factory-boy in `conftest.py`
- 100% coverage required

## Documentation
- Docs in `docs/en/` and `docs/it/` (MkDocs)
- Hosted on GitHub Pages: `https://applewebbo.github.io/organize_it/`
- When making substantial UI changes, remind user to update docs screenshots
