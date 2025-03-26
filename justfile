# Define the default recipe
default:
    @just --list

# Bootstrap the project (UV and BUN needed)
bootstrap:
    uv venv
    source .venv/bin/activate
    uv sync
    bun add -D daisyui@latest

# Run the local development server
local:
    uv run python manage.py tailwind --settings=core.settings.development runserver

# Install requirements
requirements:
    uv sync

# Update all packages
update_all:
    uv sync --upgrade

# Update a specific package
update *args:
    uv sync --upgrade-package {{ args }}

# Run database migrations
migrate:
    uv run python manage.py migrate --settings=core.settings.development

# Run tests
test *args:
    uv run python -m pytest --reuse-db -s -x {{ args }}

# Run fast tests
ftest *args:
    uv run pytest -n 8 --reuse-db --dist loadscope --exitfirst {{ args }}

# Run tests excluding mapbox and generate coverage report
mptest:
    uv run python -m pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100

# Set up Docker database
dockerdb:
    docker compose exec web python manage.py flush --no-input --settings=core.settings.production
    docker compose exec web python manage.py migrate --settings=core.settings.production
    docker compose exec web python manage.py populate_trips --settings=core.settings.production

# Run the cluster
cluster:
    python manage.py qcluster --settings=core.settings.development

lint:
    uv run ruff check --fix --unsafe-fixes .
    uv run ruff format .
    just _pre-commit run --all-files

_pre-commit *args:
    uvx --with pre-commit-uv pre-commit {{ args }}

secure:
    uv-secure

populate_trips:
    uv run python manage.py populate_trips
