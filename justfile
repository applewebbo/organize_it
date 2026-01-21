# List all available commands.
default:
    @just --list


##########################################################################
# Setup
##########################################################################

# Ensure project virtualenv is up to date
[group('setup')]
@install:
    uv sync
# Update dependencies and pre-commit hooks
[group('setup')]
@update_all: lock
    uv sync --all-extras --upgrade
    uvx --with pre-commit-uv pre-commit autoupdate

# Update a specific package
[group('setup')]
@update *args:
    uv sync --upgrade-package {{ args }}

# Rebuild lock file from scratch
[group('setup')]
@lock:
    echo "Rebuilding lock file..."
    uv lock --upgrade
    echo "Done!"

# Remove temporary files
[group('setup')]
clean:
    rm -rf .venv .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .django_tailwind_cli
    find . -type d -name "__pycache__" -exec rm -r {} +

# Recreate project virtualenv from nothing
[group('setup')]
fresh: clean install


##########################################################################
# Development
##########################################################################

# Run the local development server
[group('development')]
@local:
    uv run python manage.py tailwind runserver

# Run development server + worker with Overmind
[group('development')]
@serve:
    mprocs -c mprocs-local.yaml

# Add dummy trips to the database
[group('development')]
@populate_trips:
    uv run python manage.py populate_trips

# Create database migrations
[group('development')]
makemigrations:
    uv run python manage.py makemigrations

# Run database migrations
[group('development')]
migrate:
    uv run python manage.py migrate

# Compile Translation Files
[group('development')]
compilemessages:
    uv run python manage.py compilemessages

# Update Translation Files
[group('development')]
makemessages:
    uv run python manage.py makemessages -a

# Run Tasks Worker
[group('development')]
@tasks:
    uv run python manage.py qcluster

# Test Docker locally before deploy on Caprover
[group('development')]
@docker-test:
    docker build -t organize-it:test .
    docker run -it -p 80:80 \
        -v $(pwd)/.env.dev:/app/.env:ro \
        -e ENVIRONMENT=prod \
        organize-it:test

##########################################################################
# Utility
##########################################################################


# Run tests
[group('utility')]
test *args:
    ENVIRONMENT=test uv run python -m pytest --reuse-db -s -x {{ args }}

# Run fast tests
[group('utility')]
ftest *args:
    ENVIRONMENT=test uv run pytest -n 8 --reuse-db --dist loadscope --exitfirst {{ args }}

# Run tests excluding mapbox and generate coverage report
[group('utility')]
mptest:
    ENVIRONMENT=test uv run python -m pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100

# Run Ruff linting and formatting
[group('utility')]
lint:
    uv run ruff check --fix --unsafe-fixes .
    uv run ruff format .
    just _pre-commit run --all-files

_pre-commit *args:
    uvx prek {{ args }}

# Check for unsecured dependencies
[group('utility')]
secure:
    uv-secure


##########################################################################
# Documentation
##########################################################################

# Serve documentation locally with live reload
[group('docs')]
@docs-serve:
    echo "Starting MkDocs development server..."
    echo "Documentation will be available at http://127.0.0.1:8000"
    uv run --extra docs mkdocs serve

# Build documentation for production
[group('docs')]
@docs-build:
    echo "Building documentation..."
    uv run --extra docs mkdocs build
    echo "Documentation built in site/ directory"
