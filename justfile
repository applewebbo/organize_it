set dotenv-load

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
@update_all: lock update_phosphor
    uv sync --all-extras --upgrade
    uvx --with pre-commit-uv prek auto-update

# Download or update self-hosted Phosphor Icons (bold variant)
[group('setup')]
update_phosphor:
    #!/usr/bin/env bash
    set -euo pipefail
    STATIC_DIR="static/icons/phosphor/bold"
    VERSION_FILE="static/icons/phosphor/.version"

    NPM_META=$(curl -sf https://registry.npmjs.org/@phosphor-icons/web/latest)
    LATEST=$(echo "$NPM_META" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])")
    TARBALL=$(echo "$NPM_META" | python3 -c "import sys,json; print(json.load(sys.stdin)['dist']['tarball'])")

    CURRENT=""
    if [ -f "$VERSION_FILE" ]; then
        CURRENT=$(cat "$VERSION_FILE")
    fi

    if [ "$CURRENT" = "$LATEST" ]; then
        echo "✓ Phosphor Icons $LATEST already up to date"
        exit 0
    fi

    echo "⬇️  Updating Phosphor Icons: ${CURRENT:-none} → $LATEST"

    TMP_DIR=$(mktemp -d)
    trap "rm -rf $TMP_DIR" EXIT

    curl -sf "$TARBALL" | tar -xz -C "$TMP_DIR"

    mkdir -p "$STATIC_DIR"
    cp "$TMP_DIR/package/src/bold/style.css" "$STATIC_DIR/"
    find "$TMP_DIR/package/src/bold" \( -name "*.woff2" -o -name "*.woff" -o -name "*.ttf" \) -exec cp {} "$STATIC_DIR/" \;

    mkdir -p "$(dirname "$VERSION_FILE")"
    echo "$LATEST" > "$VERSION_FILE"
    echo "✓ Phosphor Icons $LATEST installed in $STATIC_DIR"

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
    ENVIRONMENT=test uv run pytest -n 4 --reuse-db --dist loadscope --exitfirst {{ args }}

# Run fast tests with coverage report (must reach 100%)
[group('utility')]
cov *args:
    ENVIRONMENT=test uv run pytest -n 4 --reuse-db --dist loadscope --exitfirst --cov=. --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100 {{ args }}

# Show coverage for a specific test file against a source module (no threshold)
# Usage: just fcov tests/trips/test_views_map.py trips/views/maps.py
[group('utility')]
fcov test_path source="trips":
    #!/usr/bin/env bash
    set -euo pipefail
    # Convert file path to module notation (trips/views/maps.py → trips.views.maps)
    module=$(echo "{{ source }}" | sed 's|/|.|g' | sed 's|\.py$||')
    ENVIRONMENT=test uv run pytest --reuse-db --exitfirst --cov="$module" --cov-report term-missing {{ test_path }}

# Run tests excluding mapbox and generate coverage report
[group('utility')]
mptest:
    ENVIRONMENT=test uv run python -m pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100

# Run pre-commit hooks (linting, formatting, security checks)
[group('utility')]
lint:
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
    fj issue search "" --state {{state}}

# Show issue details
[group('codeberg')]
issue number:
    fj issue view {{number}}

# Add comment to issue from a markdown file (usage: just issue-comment 360 /path/to/comment.md)
[group('codeberg')]
issue-comment number file:
    fj issue comment {{number}} --body-file {{file}}

# Mark a checkbox step as done in issue body
[group('codeberg')]
issue-check number step:
    ./bin/codeberg check {{number}} "{{step}}"

# Close issue
[group('codeberg')]
issue-close number:
    fj issue close {{number}}

# Reopen issue
[group('codeberg')]
issue-reopen number:
    #!/usr/bin/env bash
    set -euo pipefail
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    curl -s -X PATCH "https://codeberg.org/api/v1/repos/webbografico/organize_it/issues/{{number}}" \
      -H "Authorization: token ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"state":"open"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✓ Issue #{d[\"number\"]} reopened')"

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

# Add labels to issue (space-separated label names)
[group('codeberg')]
issue-label number *labels:
    #!/usr/bin/env bash
    set -euo pipefail
    for label in {{labels}}; do
        fj issue edit {{number}} labels -a "$label"
        echo "✓ Label '$label' added to issue #{{number}}"
    done

# Create a label (if missing, with random color) and assign it to an issue: just issue-label-create <issue> <label>
[group('codeberg')]
issue-label-create number name:
    #!/usr/bin/env bash
    set -euo pipefail
    COLORS=("#e11d48" "#ea580c" "#d97706" "#65a30d" "#16a34a" "#059669" "#0891b2" "#2563eb" "#7c3aed" "#c026d3" \
            "#be185d" "#b45309" "#4d7c0f" "#0e7490" "#1d4ed8" "#6d28d9" "#a21caf" "#be123c" "#15803d" "#0369a1")
    RANDOM_COLOR=${COLORS[$((RANDOM % ${#COLORS[@]}))]}
    TOKEN=$(grep "^CODEBERG_API_TOKEN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    LABEL_ID=$(curl -s "https://codeberg.org/api/v1/repos/webbografico/organize_it/labels" \
      -H "Authorization: token ${TOKEN}" | jq -r '.[] | select(.name == "{{name}}") | .id')
    if [ -z "$LABEL_ID" ]; then
        echo "Creating label '{{name}}' with color ${RANDOM_COLOR}..."
        LABEL_ID=$(curl -s -X POST "https://codeberg.org/api/v1/repos/webbografico/organize_it/labels" \
          -H "Authorization: token ${TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{\"name\":\"{{name}}\",\"color\":\"${RANDOM_COLOR}\"}" | jq -r '.id')
        echo "✓ Label '{{name}}' created (id: ${LABEL_ID})"
    else
        echo "✓ Label '{{name}}' already exists (id: ${LABEL_ID})"
    fi
    fj issue edit {{number}} labels -a "{{name}}"
    echo "✓ Label assigned to issue #{{number}}"

# Create new issue (body optional)
[group('codeberg')]
issue-create title body="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "{{body}}" ]; then
        EDITOR=true fj issue create "{{title}}" --no-template
    else
        TMPFILE=$(mktemp /tmp/issue-body-XXXXXX.md)
        echo "{{body}}" > "$TMPFILE"
        EDITOR=true fj issue create "{{title}}" --body-file "$TMPFILE" --no-template
        rm "$TMPFILE"
    fi

# Edit issue body from file (usage: just issue-edit-body 249 /path/to/body.md)
[group('codeberg')]
issue-edit-body number file:
    fj issue edit {{number}} body "$(cat {{file}})"

# List all releases
[group('codeberg')]
release-list:
    fj release list --include-draft --include-prerelease

# Show release details
[group('codeberg')]
release-show tag:
    fj release view "{{tag}}" --by-tag

# Create a new release (creates tag, pushes main+tag, creates Codeberg release via fj)
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

    # Create release via fj
    echo "🚀 Creating release on Codeberg..."
    fj release create "{{tag}}" -r webbografico/organize_it --tag "{{tag}}" --body "$(cat "$NOTES_FILE")"
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
# Tasks
##########################################################################

# List all ready/in-progress tasks
[group('tasks')]
tasks-list:
    taskdb list

# List completed tasks
[group('tasks')]
tasks-done:
    taskdb list --status done
