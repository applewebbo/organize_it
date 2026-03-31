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
    uvx --with pre-commit-uv prek auto-update

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

# Test Docker locally before deploy on Coolify
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
# Codeberg
##########################################################################

# List issues (state: open|closed|all)
[group('codeberg')]
issues state="open":
    ./bin/codeberg list {{state}}

# Show issue details
[group('codeberg')]
issue number:
    ./bin/codeberg show {{number}}

# Add comment to issue
[group('codeberg')]
issue-comment number text:
    ./bin/codeberg comment {{number}} "{{text}}"

# Mark a checkbox step as done in issue body
[group('codeberg')]
issue-check number step:
    ./bin/codeberg check {{number}} "{{step}}"

# Close issue
[group('codeberg')]
issue-close number:
    ./bin/codeberg close {{number}}

# Reopen issue
[group('codeberg')]
issue-reopen number:
    ./bin/codeberg reopen {{number}}

# Create a label if it doesn't exist (color optional, default blue)
[group('codeberg')]
label-create name color="#0075ca":
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    EXISTING=$(curl -s "https://codeberg.org/api/v1/repos/webbografico/organize_it/labels" \
      -H "Authorization: token ${TOKEN}" | jq -r '.[] | select(.name == "{{name}}") | .id')
    if [ -n "$EXISTING" ]; then
        echo "✓ Label '{{name}}' already exists (id: ${EXISTING})"
    else
        curl -s -X POST "https://codeberg.org/api/v1/repos/webbografico/organize_it/labels" \
          -H "Authorization: token ${TOKEN}" \
          -H "Content-Type: application/json" \
          -d '{"name":"{{name}}","color":"{{color}}"}' | jq -r '"✓ Label \(.name) created (id: \(.id))"'
    fi

# Add labels to issue (space-separated)
[group('codeberg')]
issue-label number *labels:
    ./bin/codeberg label {{number}} {{labels}}

# Create new issue
[group('codeberg')]
issue-create title body="":
    ./bin/codeberg create "{{title}}" "{{body}}"

# Edit issue body from file (usage: just issue-edit-body 249 /path/to/body.md)
[group('codeberg')]
issue-edit-body number file:
    fgj issue edit {{number}} --body "$(cat {{file}})"

# List all releases
[group('codeberg')]
release-list:
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    echo -e "TAG\tNAME\tPUBLISHED\tDRAFT"
    curl -s "https://codeberg.org/api/v1/repos/webbografico/organize_it/releases" \
      -H "Authorization: token ${TOKEN}" | \
      jq -r '.[] | "\(.tag_name)\t\(.name)\t\(.published_at)\t\(.draft)"' | \
      column -t -s $'\t'

# Show release details
[group('codeberg')]
release-show tag:
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    curl -s "https://codeberg.org/api/v1/repos/webbografico/organize_it/releases/tags/{{tag}}" \
      -H "Authorization: token ${TOKEN}" | \
      jq -r '"\nTag: \(.tag_name)\nName: \(.name)\nPublished: \(.published_at)\nDraft: \(.draft)\nPrerelease: \(.prerelease)\n\nURL: \(.html_url)\n\nBody:\n\(.body)\n"'

# Create a new release (creates tag, pushes main+tag, creates Codeberg release via fgj)
# Pass notes_file to use custom rich notes; omit for auto-generated notes from commits
[group('codeberg')]
release-create tag previous_tag="" notes_file="" draft="false" prerelease="false":
    #!/usr/bin/env bash
    set -euo pipefail

    # Push main to origin
    echo "📤 Pushing main to origin..."
    git push origin main
    echo "✓ main pushed to origin"

    # Check if tag already exists locally
    if git rev-parse "{{tag}}" >/dev/null 2>&1; then
        echo "✓ Tag {{tag}} already exists locally"
    else
        echo "📝 Creating tag {{tag}} on current commit..."
        git tag "{{tag}}"
        echo "✓ Tag {{tag}} created"
    fi

    # Push tag to origin (use refs/tags/ to avoid branch/tag ambiguity)
    echo "📤 Pushing tag {{tag}} to origin..."
    git push origin "refs/tags/{{tag}}"
    echo "✓ Tag {{tag}} pushed to origin"

    # Determine notes file
    if [ "{{notes_file}}" != "" ]; then
        NOTES_FILE="{{notes_file}}"
        echo "📄 Using provided notes file: ${NOTES_FILE}"
    else
        # Auto-generate notes to a temp file
        NOTES_FILE=$(mktemp /tmp/release-notes-XXXXXX.md)

        # Determine previous tag if not provided
        if [ "{{previous_tag}}" = "" ]; then
            PREV_TAG=$(git tag --sort=-version:refname | grep -v "{{tag}}" | head -1)
        else
            PREV_TAG="{{previous_tag}}"
        fi

        echo "🔍 Generating release notes (comparing with ${PREV_TAG})..."
        COMMITS=$(git log ${PREV_TAG}..{{tag}} --pretty=format:"- %s" --reverse 2>/dev/null || echo "- Initial release")

        FEATURES=$(echo "$COMMITS" | grep -E "^- (✨|feat)" || true)
        FIXES=$(echo "$COMMITS" | grep -E "^- (🐛|fix)" || true)
        CHORES=$(echo "$COMMITS" | grep -E "^- (🔧|chore|📦|build|🎨)" || true)
        TESTS=$(echo "$COMMITS" | grep -E "^- (🧪|test|✅)" || true)
        DOCS=$(echo "$COMMITS" | grep -E "^- (📚|docs)" || true)

        {
            echo "## What's New in {{tag}}"
            echo ""
            if [ -n "$FEATURES" ]; then
                echo "### 🚀 Features"
                echo "$FEATURES"
                echo ""
            fi
            if [ -n "$FIXES" ]; then
                echo "### 🐛 Bug Fixes"
                echo "$FIXES"
                echo ""
            fi
            if [ -n "$CHORES" ]; then
                echo "### 🛠️ Maintenance"
                echo "$CHORES"
                echo ""
            fi
            if [ -n "$TESTS" ]; then
                echo "### 🧪 Testing"
                echo "$TESTS"
                echo ""
            fi
            if [ -n "$DOCS" ]; then
                echo "### 📖 Documentation"
                echo "$DOCS"
                echo ""
            fi
            echo "### 📖 Full Changelog"
            echo "https://codeberg.org/webbografico/organize_it/compare/${PREV_TAG}...{{tag}}"
        } > "$NOTES_FILE"
    fi

    # Create release via fgj
    echo "🚀 Creating release on Codeberg..."
    fgj release create "{{tag}}" --repo webbografico/organize_it --title "{{tag}}" --notes-file "$NOTES_FILE"
    echo ""
    echo "✓ Release {{tag}} created!"


##########################################################################
# Documentation
##########################################################################

# Serve documentation locally with live reload
[group('docs')]
@docs-serve:
    echo "Starting MkDocs development server..."
    echo "Documentation will be available at http://127.0.0.1:8000"
    uv run --group docs mkdocs serve

# Build documentation for production
[group('docs')]
@docs-build:
    echo "Building documentation..."
    uv run --group docs mkdocs build
    echo "Documentation built in site/ directory"

##########################################################################
# Beans
##########################################################################

# List active beans (excludes completed and scrapped)
[group('beans')]
beans:
    beans list --ready

# List completed beans
[group('beans')]
beans_completed:
    beans list -s completed
