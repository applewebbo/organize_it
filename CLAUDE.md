# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Workflow (CRITICAL - READ FIRST)

**ALWAYS follow these rules before making any code changes:**

1. **NEVER work directly on main branch** - Always create a feature branch first
2. **Create feature branches** with descriptive names: `feature/description` or `fix/issue-description`
3. **Ask for GitHub issue number** - Always ask the user which issue number this work relates to
4. **Make frequent commits** - Commit logical chunks of work to better track changes
5. **Reference issues in commits** - Include `Fix #123` or `Related to #123` in commit messages
6. **Test before committing** - Run `just ftest` to ensure 100% coverage before committing
7. **Use rebase, not merge** - When ready to save changes to main: `git checkout main && git rebase feature-branch`
8. **Verify coverage** - Always check that coverage remains at 100% before final commit to main

### Standard Workflow
```bash
# 1. Ask user for issue number first
# 2. Create feature branch
git checkout -b feature/descriptive-name

# 3. Make changes and commit frequently
git add <files>
git commit -m "descriptive message (for #123)"

# 4. Before final commit, verify tests
just ftest

# 5. Only use (fix #123) instead of (for #123)  on final commit

# 6. When ready, rebase onto main
git checkout main
git rebase feature/descriptive-name

# 7. Verify everything still works
just ftest

# 8. Push to remote
git push origin main
```

### Commit Message Guidelines

- Write clear, descriptive commit messages
- Reference issue numbers with `fix #123` or `for #123`
- **DO NOT include attribution lines** like:
  - `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
  - `Co-Authored-By: Claude <noreply@anthropic.com>`
- Keep commit messages concise and focused on the changes made

## Project Overview

Organize It is a Django-based web application for organizing trips and travel plans. Built with Django 6.0+, TailwindCSS (with DaisyUI), HTMX, and Alpine.js, it provides a modern, reactive user experience without heavy frontend frameworks.

## Tech Stack

- **Backend**: Django 6.0+, Python 3.14+
- **Database**: SQLite (dev), PostgreSQL (production)
- **Frontend**: TailwindCSS with DaisyUI, HTMX, Alpine.js
- **Template System**: Django templates with django-cotton components
- **Auth**: django-allauth (email-based, no username)
- **Task Queue**: django-q2 for background tasks
- **Maps**: Mapbox for geocoding, Folium for map rendering
- **Images**: Pillow for image processing, Unsplash API for photo search
- **Package Manager**: uv (not pip)

## Development Commands

All commands use `just` (justfile). Never use `pip` - always use `uv`.

### Setup
- `just install` - Install/sync dependencies
- `just update_all` - Update all dependencies and pre-commit hooks
- `just clean` - Remove temporary files and caches
- `just fresh` - Complete clean reinstall

### Running the App
- `just local` - Run development server with Tailwind compilation
- `just serve` - Run web + worker together with Overmind (recommended)
- `just tasks` - Run django-q2 background task worker manually
- `just migrate` - Run database migrations
- `just makemigrations` - Create new migrations

### Testing
- `just test` - Run all tests with pytest (single-threaded, verbose)
- `just ftest` - Run tests in parallel (8 workers, fast)
- `just mptest` - Run tests excluding mapbox tests with coverage
- Test files are in `tests/` directory (not in app directories)
- Always use pytest with fixtures from `conftest.py` and factory-boy
- Target 100% code coverage (configured in pyproject.toml)

### Code Quality
- `just lint` - Run ruff linting, formatting, and pre-commit hooks

## Architecture

### Models Architecture

The app has two main Django apps: `accounts` and `trips`.

**Core Entity Relationships:**
- `Trip` (1) → (many) `Day` - A trip contains multiple days
- `Trip` (many) → (many) `Link` - A trip can have multiple links (URLs)
- `Day` (1) → (many) `Event` - Each day can have multiple events
- `Day` (1) → (0-1) `Stay` - Each day can have one stay (hotel, etc.)
- `Event` is a polymorphic parent model with three child types:
  - `Transport` - Movement between locations (has destination field)
  - `Experience` - Activities, museums, walks, etc.
  - `Meal` - Restaurants, food experiences
- `Trip` (1) → (many) `Event` via `all_events` - Direct trip→event relationship for orphaned events

**Key Model Behaviors:**
- Trip status auto-updates based on dates (NOT_STARTED → IMPENDING → IN_PROGRESS → COMPLETED → ARCHIVED)
- Trip images can be uploaded directly or searched/downloaded from Unsplash with attribution tracking
- Days auto-generate/update when trip dates change via `update_trip_days` signal (trips/models.py:63)
- Events can be "unpaired" (day=None) and later paired to days
- Stays can span multiple consecutive days
- All location-based models (Event, Stay) auto-geocode addresses on save using Mapbox
- Single Table Inheritance pattern: Transport/Experience/Meal extend Event with category field

### Views Architecture

**All views are function-based** (FBV preferred over CBV per coding guidelines). Most views use HTMX for interactivity:

- HTMX views check `request.htmx` and return template fragments using `#fragment` syntax
- Most mutations return `HttpResponse(status=204, headers={"HX-Trigger": "..."})`
- Uses `get_object_or_404` for safety and `@login_required` for auth

**Optimization patterns:**
- Uses `prefetch_related` and `select_related` heavily to avoid N+1 queries
- `annotate_event_overlaps` function (trips/utils.py) uses window functions to detect time conflicts
- Day-based queries always prefetch events and stays together

### Forms & Geocoding

Forms use crispy-forms with crispy-tailwind template pack. Two geocoding approaches:

1. **Model-level geocoding**: Event/Stay models geocode on save if address changes (using Mapbox)
2. **Form-level geocoding**: Some forms (ExperienceForm, MealForm, StayForm) have `geocode` parameter to enable/disable auto-geocoding
3. **User-assisted geocoding**: `geocode_address` view (trips/views.py:700) uses Nominatim/OpenStreetMap for user-driven location search

### Template Structure

- Base templates: `templates/base.html` and `templates/base-simplified.html`
- Cotton components: `templates/cotton/` (reusable UI components)
- App templates: `templates/trips/` (trip-specific views)
- Template inheritance uses django-cotton for component composition
- Template fragments (using `#fragment` syntax) allow partial rendering for HTMX swaps

### Background Tasks

Django-Q2 handles async tasks with environment-specific configuration:

**Configuration**:
- **Development**: ORM-based queue, 4 workers (configurable via env)
- **Production**: Redis-based queue, 4 workers (configurable via env)
- **Test**: Synchronous execution (sync=True), 1 worker

**Available Tasks** (trips/tasks.py):
- `check_trips_status()` - Update trip statuses based on dates
- `cleanup_old_sessions()` - Delete expired sessions
- `backup_database()` - Backup database using django-dbbackup
- `populate_trips()` - Populate with dummy trips (dev only)

**Scheduled Tasks** (configured in settings.py):
- **Development**:
  - `check_trips_status` - Every hour (for testing)
- **Production**:
  - `check_trips_status` - Daily at 3 AM
  - `cleanup_old_sessions` - Weekly
  - `backup_database` - Every Sunday at 2 AM

**Worker Management**:
- `just tasks` - Run worker manually
- `just serve` - Run web + worker with Overmind (recommended for dev)
- Production: Uses `Procfile` with Gunicorn + worker process

**Configuration Variables** (.env):
```bash
# Worker configuration (optional, has defaults)
Q_CLUSTER_WORKERS=4
Q_CLUSTER_TIMEOUT=90
Q_CLUSTER_RETRY=120
Q_CLUSTER_MAX_ATTEMPTS=3
Q_CLUSTER_QUEUE_LIMIT=50

# Redis (production only)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

Tasks log to `tasks.log` file (configured in settings.LOGGING)

### Authentication

- Custom user model: `accounts.CustomUser` (email-based, no username field)
- All users get auto-created `Profile` via signal (accounts/models.py:38)
- django-allauth handles email verification (mandatory), login, signup
- Email backend: console (dev), Mailgun (production)

## Configuration

### Environment Variables

Required in `.env`:
- `SECRET_KEY` - Django secret key
- `ENVIRONMENT` - "dev", "prod", or "test"
- `MAPBOX_ACCESS_TOKEN` - For geocoding
- `GOOGLE_PLACES_API_KEY` - For enriching events/stays (optional)
- `UNSPLASH_ACCESS_KEY` - For Unsplash photo search/download (optional)

Production-specific:
- Database config: `SQL_ENGINE`, `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD`, `SQL_HOST`, `SQL_PORT`
- Mailgun: `MAILGUN_API_KEY`, `MAILGUN_API_URL`, `MAILGUN_SENDER_DOMAIN`
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
- Django-Q2 workers: `Q_CLUSTER_WORKERS`, `Q_CLUSTER_TIMEOUT`, `Q_CLUSTER_RETRY`, `Q_CLUSTER_MAX_ATTEMPTS`, `Q_CLUSTER_QUEUE_LIMIT`
- Dropbox backup: `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_OAUTH2_ACCESS_TOKEN`, `DROPBOX_OAUTH2_REFRESH_TOKEN`

### Settings Structure

Single `core/settings.py` file with environment-based conditionals:
- Lines 315-350: Development settings (DEBUG=True, SQLite, console email, ORM-based Q_CLUSTER)
- Lines 352-415: Production settings (PostgreSQL, Mailgun email, Redis-based Q_CLUSTER)
- Lines 418-439: Test settings (in-memory SQLite, fast password hashing, sync Q_CLUSTER)

## Coding Standards (from .github/copilot-instructions.md)

### Python/Django
- PEP 8 with 120 character line limit
- Double quotes for strings
- f-strings for formatting
- isort for import sorting
- Function-based views preferred over class-based
- Use Django ORM, avoid raw SQL
- Use signals sparingly and document them

### Models
- Always include `__str__` methods
- Use `related_name` for foreign keys
- Define `Meta` class with ordering/verbose_name
- `blank=True` for optional forms, `null=True` for optional DB fields

### Views
- Use `get_object_or_404` instead of manual exception handling
- Validate/sanitize all user input
- Handle exceptions with try/except

### Testing
- All tests in `tests/` directory (not in apps)
- Use pytest, pytest-django, django-test-plus, factory-boy
- Add `pytestmark = pytest.mark.django_db` for DB tests
- Test positive and negative scenarios
- Don't test Django internals

### Naming Conventions
- Templates: kebab-case (e.g., `trip-detail.html`)
- Functions/variables: snake_case
- Models: PascalCase, singular nouns
- Constants: UPPERCASE

### Frontend
- HTMX for SPA-like features with django-htmx middleware
- Alpine.js for client-side interactivity
- Use static files with `{% load static %}`
- Keep logic out of templates

## Google Places Enrichment

Events and Stays can be "enriched" with additional data from Google Places API:
- Two-step process: 1) Search for place_id, 2) Fetch details (website, phone, hours)
- Views: `enrich_event` (trips/views.py:1000), `enrich_stay` (trips/views.py:874)
- Requires `GOOGLE_PLACES_API_KEY` environment variable
- Sets `enriched=True` flag and populates `opening_hours` JSON field

## Unsplash Integration

Trip cover images can be searched and downloaded from Unsplash:
- **Search**: `search_unsplash_photos()` (trips/utils.py) - Search Unsplash photos with caching
- **Download**: `download_unsplash_photo()` (trips/utils.py) - Download photo and trigger tracking endpoint (TOS requirement)
- **Attribution**: Trip model tracks image metadata for Unsplash attribution requirements
- **Views**: Integrated into trip create/edit forms with HTMX search endpoint
- Requires `UNSPLASH_ACCESS_KEY` environment variable
- Images are processed with Pillow for optimization before storage

## Common Patterns

### HTMX Response Pattern
```python
if form.is_valid():
    obj = form.save()
    messages.add_message(request, messages.SUCCESS, "Success!")
    return HttpResponse(status=204, headers={"HX-Trigger": "tripModified"})
```

### Prefetch Pattern for Day Views
```python
qs = Day.objects.prefetch_related(
    Prefetch(
        "events",
        queryset=annotate_event_overlaps(Event.objects.all()).order_by("start_time"),
    ),
    "stay",
).select_related("trip__author")
```

### Polymorphic Event Handling
```python
event = get_event_instance(event)  # Returns Transport/Experience/Meal instance
```

## Important Notes

- Never use `pip` - always use `uv` for package management
- Tests must achieve 100% coverage (see pyproject.toml)
- Use `just` for all commands (see justfile)
- Template fragments use `#fragment` syntax for HTMX partial rendering
- All location models geocode automatically on address change
- Events can exist without a day (orphaned) for later scheduling
- Trip images from Unsplash require proper attribution (automatically tracked via `image_metadata`)
