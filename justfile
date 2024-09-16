
# Define the default recipe
default:
    @just --list

# Run the local development server
local:
    python manage.py tailwind --settings=core.settings.development runserver

# Install requirements
requirements:
    uv sync

# Update all packages
update_all:
    uv sync --upgrade

# Update a specific package
update package:
    uv sync --upgrade-package

# Run database migrations
migrate:
    python manage.py migrate --settings=core.settings.development

# Run tests
test:
    COVERAGE_CORE=sysmon python -m pytest --reuse-db -s

# Run fast tests
ftest:
    pytest -n 8 --reuse-db

# Run tests excluding mapbox and generate coverage report
mptest:
    COVERAGE_CORE=sysmon python -m pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100

# Set up Docker database
dockerdb:
    docker compose exec web python manage.py flush --no-input --settings=core.settings.production
    docker compose exec web python manage.py migrate --settings=core.settings.production
    docker compose exec web python manage.py populate_trips --settings=core.settings.production

# Run the cluster
cluster:
    python manage.py qcluster --settings=core.settings.development
