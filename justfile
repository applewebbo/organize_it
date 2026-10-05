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
# Update dependencies, vendored JS libs and pre-commit hooks
[group('setup')]
@update_all: lock update_js
    uv sync --all-extras --upgrade
    uvx --with pre-commit-uv prek update

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

# Verify every Phosphor icon referenced in templates exists in the self-hosted set
[group('setup')]
check_phosphor:
    #!/usr/bin/env bash
    set -euo pipefail
    CSS="static/icons/phosphor/bold/style.css"
    AVAILABLE=$(grep -oE '\.ph-bold\.ph-[a-z0-9-]+:before' "$CSS" | sed -E 's/.*\.(ph-[a-z0-9-]+):before/\1/' | sort -u)
    USED=$(grep -rhoE 'ph-[a-z0-9-]+' templates/ | grep -vE '^ph-(bold|thin|light|regular|fill|duotone)$' | sort -u)
    MISSING=$(comm -23 <(echo "$USED") <(echo "$AVAILABLE"))
    if [ -n "$MISSING" ]; then
        echo "❌ Phosphor icons used in templates but missing from the set:"
        echo "$MISSING"
        exit 1
    fi
    echo "✓ All Phosphor icons used in templates are present"

# Update self-hosted Phosphor Icons then verify every used icon exists
[group('setup')]
phosphor: update_phosphor check_phosphor

# Download or update the vendored Alpine.js core + plugins (collapse, focus)
[group('setup')]
update_js:
    #!/usr/bin/env bash
    set -euo pipefail
    STATIC_DIR="static/js"
    VERSION_FILE="static/js/.alpine-version"

    get_latest() { curl -sf "https://registry.npmjs.org/$1/latest" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"; }

    ALPINE_LATEST=$(get_latest alpinejs)
    COLLAPSE_LATEST=$(get_latest @alpinejs/collapse)
    FOCUS_LATEST=$(get_latest @alpinejs/focus)
    LATEST="alpine=$ALPINE_LATEST collapse=$COLLAPSE_LATEST focus=$FOCUS_LATEST"

    CURRENT=""
    if [ -f "$VERSION_FILE" ]; then
        CURRENT=$(cat "$VERSION_FILE")
    fi

    if [ "$CURRENT" = "$LATEST" ]; then
        echo "✓ Alpine.js ($LATEST) already up to date"
        exit 0
    fi

    echo "⬇️  Updating Alpine.js: ${CURRENT:-none} → $LATEST"

    curl -sf "https://cdn.jsdelivr.net/npm/alpinejs@${ALPINE_LATEST}/dist/cdn.min.js" -o "$STATIC_DIR/alpine.min.js"
    curl -sf "https://cdn.jsdelivr.net/npm/@alpinejs/collapse@${COLLAPSE_LATEST}/dist/cdn.min.js" -o "$STATIC_DIR/alpine-collapse.min.js"
    curl -sf "https://cdn.jsdelivr.net/npm/@alpinejs/focus@${FOCUS_LATEST}/dist/cdn.min.js" -o "$STATIC_DIR/alpine-focus.min.js"

    echo "$LATEST" > "$VERSION_FILE"
    echo "✓ Alpine.js ($LATEST) installed in $STATIC_DIR"

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

# Run development server + worker with mprocs (now `dekit`, upstream renamed the project)
[group('development')]
@serve:
    dekit mprocs -c mprocs-local.yaml

# Add dummy trips to the database
[group('development')]
@populate_trips:
    uv run python manage.py populate_trips

# Crawl the site for broken links / runtime errors (needs a populated dev DB)
[group('development')]
crawl *args:
    ENVIRONMENT=dev uv run python manage.py crawl -v 2 {{ args }}

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

# Run fast tests (TEST_WORKERS controls parallelism, default 4; raise it for faster CI runs)
# taskpolicy -b routes the xdist workers to the efficiency cores (background QoS) so the
# performance cores stay free and the Mac remains responsive during the run. Default 4 matches
# the Apple-silicon efficiency-core count so the run stays fast while the P-cores stay idle.
[group('utility')]
ftest *args:
    taskpolicy -b nice -n 10 env ENVIRONMENT=test uv run pytest -n ${TEST_WORKERS:-4} --reuse-db --dist loadscope --exitfirst {{ args }}

# Run fast tests with coverage report (must reach 100%)
[group('utility')]
cov *args:
    taskpolicy -b nice -n 10 env ENVIRONMENT=test uv run pytest -n ${TEST_WORKERS:-4} --reuse-db --dist loadscope --exitfirst --cov=. --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100 {{ args }}

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

# Run pre-commit hooks (linting, formatting, security checks); niced to keep the machine responsive
[group('utility')]
lint:
    nice -n 10 just _pre-commit run --all-files

_pre-commit *args:
    uvx prek {{ args }}

# Check for unsecured dependencies
[group('utility')]
secure:
    uv-secure


##########################################################################
# GitHub
##########################################################################

# Target GitHub repository for all gh commands (origin may still point elsewhere)
github_repo := "applewebbo/organize_it"

# List issues (state: open|closed|all)
[group('github')]
issues state="open":
    gh issue list -R {{github_repo}} --state {{state}}

# Show issue details (body + comments if any)
[group('github')]
issue number:
    #!/usr/bin/env bash
    set -euo pipefail
    gh issue view {{number}} -R {{github_repo}}
    comments=$(gh issue view {{number}} -R {{github_repo}} --comments)
    if [ -n "$comments" ]; then
        printf '\n--- Comments ---\n%s\n' "$comments"
    fi

# Add comment to issue from a markdown file (usage: just issue-comment 360 /path/to/comment.md)
[group('github')]
issue-comment number file:
    gh issue comment {{number}} -R {{github_repo}} --body-file {{file}}

# Close issue
[group('github')]
issue-close number:
    gh issue close {{number}} -R {{github_repo}}

# Reopen issue
[group('github')]
issue-reopen number:
    gh issue reopen {{number}} -R {{github_repo}}

# Create a label if it doesn't exist (color optional, default blue). --force updates it if present.
[group('github')]
label-create name color="0075ca":
    gh label create "{{name}}" -R {{github_repo}} --color "{{color}}" --force

# Add labels to issue (space-separated label names)
[group('github')]
issue-label number *labels:
    #!/usr/bin/env bash
    set -euo pipefail
    for label in {{labels}}; do
        gh issue edit {{number}} -R {{github_repo}} --add-label "$label"
        echo "✓ Label '$label' added to issue #{{number}}"
    done

# Create a label (if missing, with random color) and assign it to an issue: just issue-label-create <issue> <label>
[group('github')]
issue-label-create number name:
    #!/usr/bin/env bash
    set -euo pipefail
    # Create the label with a random color only when it doesn't already exist,
    # so re-assigning an existing label keeps its current color.
    if gh label list -R {{github_repo}} --limit 999 --json name -q '.[].name' | grep -qxF "{{name}}"; then
        echo "• Label '{{name}}' already exists, keeping its color"
    else
        COLORS=("e11d48" "ea580c" "d97706" "65a30d" "16a34a" "059669" "0891b2" "2563eb" "7c3aed" "c026d3" \
                "be185d" "b45309" "4d7c0f" "0e7490" "1d4ed8" "6d28d9" "a21caf" "be123c" "15803d" "0369a1")
        RANDOM_COLOR=${COLORS[$((RANDOM % ${#COLORS[@]}))]}
        gh label create "{{name}}" -R {{github_repo}} --color "${RANDOM_COLOR}"
    fi
    gh issue edit {{number}} -R {{github_repo}} --add-label "{{name}}"
    echo "✓ Label '{{name}}' assigned to issue #{{number}}"

# Create new issue (body optional)
[group('github')]
issue-create title body="":
    gh issue create -R {{github_repo}} --title "{{title}}" --body "{{body}}"

# Edit issue body from file (usage: just issue-edit-body 249 /path/to/body.md)
[group('github')]
issue-edit-body number file:
    gh issue edit {{number}} -R {{github_repo}} --body-file {{file}}

# List all releases
[group('github')]
release-list:
    gh release list -R {{github_repo}}

# Show release details
[group('github')]
release-show tag:
    gh release view "{{tag}}" -R {{github_repo}}

# Create a new release (creates tag, pushes main+tag, creates GitHub release via gh)
# Pass notes_file to use custom rich notes; omit for auto-generated notes from commits
[group('github')]
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
            echo "https://github.com/{{github_repo}}/compare/${PREV_TAG}...{{tag}}"
        } > "$NOTES_FILE"
    fi

    # Build gh release flags
    RELEASE_FLAGS=(--title "{{tag}}" --notes-file "$NOTES_FILE")
    if [ "{{previous_tag}}" != "" ]; then
        RELEASE_FLAGS+=(--verify-tag)
    fi
    if [ "{{draft}}" = "true" ]; then
        RELEASE_FLAGS+=(--draft)
    fi
    if [ "{{prerelease}}" = "true" ]; then
        RELEASE_FLAGS+=(--prerelease)
    fi

    # Create release via gh
    echo "🚀 Creating release on GitHub..."
    gh release create "{{tag}}" -R {{github_repo}} "${RELEASE_FLAGS[@]}"
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
