# Claude Code Skills

Custom skills available for common Django workflows. Use these for automated quality checks and safe operations.

## Available Skills

### `/makemigrations` - Safe Migration Creation
**Use when:** Modifying Django models

**What it does:**
1. Runs `just ftest` to ensure tests pass before creating migrations
2. Shows preview with `--dry-run` to review changes
3. Detects dangerous operations (RenameField, RemoveField, AddField without default)
4. Asks for confirmation before creating
5. Creates migrations and re-runs tests to verify
6. Reminds to commit migrations and update related beans

**Example workflow:**
```bash
# After modifying models.py
/makemigrations
# Review preview, confirm
# Migrations created and tested
# Then: /commit to commit migrations
```

### `/check-all` - Comprehensive Health Check
**Use when:** Before commits, before deployments, during code reviews

**What it does:**
1. Django system checks (dev + deploy mode)
2. Migration status verification
3. Code quality check (`just lint`)
4. Security audit (`just secure`)
5. Full test suite with 100% coverage (`just ftest`)
6. Counts TODO/FIXME comments
7. Lists open beans

**Output:** Health report with overall status (HEALTHY / NEEDS ATTENTION / FAILING)

**Recommended:** Run before every important commit or merge

### `/pre-deploy` - Pre-Deployment Checklist
**Use when:** Before production deployments

**What it does:**
1. Runs full `/check-all` health check
2. Verifies production settings:
   - `DEBUG = False`
   - `SECRET_KEY` from environment
   - `ALLOWED_HOSTS` configured
   - CSRF/Session cookie security enabled
3. Tests static files collection (`collectstatic --dry-run`)
4. Builds and tests Docker image (`just docker-test`)
5. Verifies git status (clean, correct branch, synced with remote)
6. Presents interactive deployment checklist
7. Provides deployment commands and recommendations

**Critical:** MUST be run before every production deployment

### `/db-backup` - Database Backup
**Use when:** Before risky operations, before deployments, periodic backups

**What it does:**
1. Checks disk space and database status
2. Creates timestamped JSON backup with `dumpdata` (portable format)
3. Creates timestamped SQLite backup (fast restore)
4. Verifies backup integrity
5. Compresses backups with gzip
6. Shows restore commands
7. Suggests backup rotation policy

**Output:** Two backup files:
- `backups/db_backup_YYYYMMDD_HHMMSS.json.gz` (portable, for migration)
- `backups/db_sqlite3_YYYYMMDD_HHMMSS.db.gz` (fast restore)

**Backup before:**
- Migrations with potential data loss
- Database schema changes
- Production deployments
- Database reset operations

### `/review` - Automated Code Review
**Use when:** Before merging a branch, during PR review, before release

**What it does:**
1. Analyzes `git diff main...HEAD` (all branch changes)
2. Checks for bugs, logic errors, N+1 queries
3. Security review (OWASP Top 10, Django-specific)
4. Verifies project pattern compliance (FBV, HTMX, Crispy Forms)
5. Checks test coverage for changed code
6. Generates report with severity levels (CRITICAL/WARNING/SUGGESTION)

**Output:** Review report with verdict (APPROVED / NEEDS CHANGES / BLOCKED)

**Different from `/check-all`:** Reviews only *changed code*, not overall project health

### `/release` - Complete Release Workflow
**Use when:** Ready to ship a release branch to production

**What it does:**
1. Validates release branch and runs all checks
2. Generates categorized release notes from commits
3. Fetches issue details to enrich release descriptions
4. Merges to main with `--ff-only` (linear history)
5. Creates tag and pushes to origin
6. Creates Codeberg release with detailed, human-readable release notes
7. Labels closed issues with release version
8. Optionally creates next release branch

**Critical:** Ensures linear history on main with fast-forward only merges

### `/deploy` - Deploy to Production (Caprover)
**Use when:** Ready to deploy to production after a release or hotfix

**What it does:**
1. Validates branch (warns if not on `main`), clean working tree and remote sync
2. Runs quick health check (tests, lint, Django check, migrations)
3. Asks which deploy mode to use:
   - `--default`: deploy current branch directly (fast, no prompts)
   - interactive: choose app/branch from Caprover CLI
4. Shows confirmation summary before deploying
5. Runs `caprover deploy` streaming output in real time
6. Verifies the app is up with an HTTP health check
7. Displays deploy summary

**App:** `organize-it` on Caprover
**entrypoint.sh:** `migrate → tailwind build → collectstatic → granian`

**Note:** Caprover keeps the previous image on failure — no downtime on broken deploys

### `/deps-update` - Safe Dependency Updates
**Use when:** Weekly maintenance, security patches, package upgrades

**What it does:**
1. Backs up current `uv.lock` before updating
2. Runs baseline tests to verify starting state
3. Updates dependencies (all or specific package)
4. Runs full test suite + security audit after update
5. Shows version diff (old → new) with major bump warnings
6. **Automatic rollback** if tests fail after update

**Safety:** Never leaves the project in a broken state

### `/cleanup` - Project Maintenance
**Use when:** Monthly maintenance, before releases, when disk space is low

**What it does:**
1. Cleans Python caches (`__pycache__`, `.pyc`, `.pyo`)
2. Clears expired Django sessions
3. Cleans test artifacts (`htmlcov/`, `.pytest_cache/`, `.ruff_cache/`)
4. Optimizes SQLite (`VACUUM`, `ANALYZE`, integrity check)
5. Reports on old backups and suggests rotation

**Output:** Cleanup report with space recovered and database health status

## Recommended Workflows

### Normal Development
```bash
# 1. Make code changes
# 2. Verify everything is OK
/check-all

# 3. If all checks pass, commit
/commit
```

### Model Changes
```bash
# 1. Modify models.py
# 2. Create migrations safely
/makemigrations

# 3. Review and commit migrations
/commit
```

### Before Merging a Branch
```bash
# 1. Review all branch changes
/review

# 2. Fix any critical/warning issues
# 3. Commit fixes and review again
/commit
/review
```

### Release Cycle
```bash
# 1. Review branch changes
/review

# 2. If approved, run full release workflow
/release

# 3. Deploy to production
/deploy
```

### Pre-Deployment (manual checklist)
```bash
# 1. Backup database first
/db-backup

# 2. Run comprehensive pre-deployment checks
/pre-deploy

# 3. Deploy to production
/deploy
```

### Weekly Maintenance
```bash
# 1. Update dependencies safely
/deps-update

# 2. Clean caches and optimize DB
/cleanup

# 3. Commit dependency updates
/commit
```

### Before Risky Operations
```bash
# Always backup first
/db-backup

# Then proceed with risky operation
# (migrations, schema changes, bulk updates, etc.)
```

## Skill Integration with Beans

- **`/makemigrations`**: Reminds to update related beans after creating migrations
- **`/check-all`**: Shows count of open beans ready to work on
- **`/pre-deploy`**: Suggests marking completed beans as done before release
- **`/release`**: Updates beans to completed and adds release version metadata
- **`/commit`**: Include bean file changes in commits when using beans for task tracking

## Best Practices

1. **Use `/check-all` liberally**: Run before every significant commit
2. **Use `/review` before merges**: Catch issues before they reach main
3. **Never skip `/pre-deploy`**: Critical for production safety
4. **Backup before risk**: Use `/db-backup` before any potentially destructive operation
5. **Update deps weekly**: Use `/deps-update` to keep dependencies secure and current
6. **Clean monthly**: Use `/cleanup` to keep the project lean and the database optimized
7. **Deploy with `/deploy`**: Never run `caprover deploy` manually — the skill validates everything first
8. **Trust the automation**: Skills handle edge cases and provide comprehensive checks
9. **Follow the prompts**: Skills ask for confirmation when needed - review carefully
