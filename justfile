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
    uv run python manage.py tailwind --settings=core.settings.development runserver

# Add dummy trips to the database
[group('development')]
@populate_trips:
    uv run python manage.py populate_trips

# Create database migrations
[group('development')]
makemigrations:
    uv run python manage.py makemigrations --settings=core.settings.development

# Run database migrations
[group('development')]
migrate:
    uv run python manage.py migrate --settings=core.settings.development

# Compile Translation Files
[group('development')]
compilemessages:
    uv run python manage.py compilemessages --settings=core.settings.development

# Update Translation Files
[group('development')]
makemessages:
    uv run python manage.py makemessages -a --settings=core.settings.development

# Run Tasks Worker
[group('development')]
@tasks:
    uv run python manage.py qcluster --settings=core.settings.development

##########################################################################
# Utility
##########################################################################


# Run tests
[group('utility')]
test *args:
    uv run python -m pytest --reuse-db -s -x {{ args }}

# Run fast tests
[group('utility')]
ftest *args:
    uv run pytest -n 8 --reuse-db --dist loadscope --exitfirst {{ args }}

# Run tests excluding mapbox and generate coverage report
[group('utility')]
mptest:
    uv run python -m pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100

# Run Ruff linting and formatting
[group('utility')]
lint:
    uv run ruff check --fix --unsafe-fixes .
    uv run ruff format .
    just _pre-commit run --all-files

_pre-commit *args:
    uvx --with pre-commit-uv pre-commit {{ args }}

# Check for unsecured dependencies
[group('utility')]
secure:
    uv-secure
