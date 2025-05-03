# List all available commands.
default:
    @just --list


##########################################################################
# Setup
##########################################################################

# Download and install uv.
[group('setup')]
uv-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "$(uname -s)" = "Windows_NT" ]; then
        echo "# For Windows, please visit https://docs.astral.sh/uv/getting-started/installation/ for instructions on how to install uv."
        exit 1
    fi
    if ! command -v uv &> /dev/null;
    then
      echo "uv is not found on path! Starting install..."
      curl -LsSf https://astral.sh/uv/install.sh | sh
    else
      uv self update
    fi

# Update uv
[group('setup')]
@uv-update:
    uv self update

# Uninstall uv
[group('setup')]
@uv-uninstall:
    uv self uninstall

# Set up the project and update dependencies
[group('setup')]
@bootstrap: uv-install
    uv sync --all-groups --upgrade

# Upgrade all dependencies to latest versions
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

# Update Translation Files
[group('development')]
compilemessages:
    uv run python manage.py compilemessages --settings=core.settings.development

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
