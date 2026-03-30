---
# db
title: Add database connection pooling
status: todo
type: task
priority: "3"
created_at: 2026-03-30T13:06:33Z
updated_at: 2026-03-30T15:08:30Z
---

# Add database connection pooling

## Objective
Reduce DB latency by 20-30% with connection pooling.

## Required changes

### 1. `core/settings.py` - DATABASES configuration (line ~136)
```python
# PRODUCTION SPECIFIC SETTINGS
if ENVIRONMENT == "prod":
    DATABASES = {
        "default": {
            "ENGINE": env("SQL_ENGINE"),
            "NAME": env("SQL_DATABASE"),
            "USER": env("SQL_USER"),
            "PASSWORD": env("SQL_PASSWORD"),
            "HOST": env("SQL_HOST"),
            "PORT": env("SQL_PORT"),
            # Connection pooling
            "CONN_MAX_AGE": 600,  # Keep connections alive for 10 min
            "CONN_HEALTH_CHECKS": True,  # Check connection health before reuse
            # Pool settings (psycopg3)
            "OPTIONS": {
                "min_size": 5,  # Minimum pool size
                "max_size": 20,  # Maximum pool size
            },
        }
    }
```

### 2. `entrypoint.sh` - PgBouncer setup (optional)
```bash
#!/bin/bash

# If using PgBouncer sidecar
if [ -n "$PGBOUNCER_HOST" ]; then
    export SQL_HOST="$PGBOUNCER_HOST"
    export SQL_PORT="6432"  # PgBouncer default port
fi

# Run migrations
python manage.py migrate --noinput

# Start Granian
exec granian core.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

### 3. `Dockerfile` - Install psycopg3-binary (if not already present)
```dockerfile
RUN pip install psycopg[binary]>=3.2.1
```

### 4. `.env.example` - Add pooling variables
```bash
# Database connection pooling
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_CONN_MAX_AGE=600
```

## Test
1. Configure environment variables for local test
2. Monitor connections with `SELECT * FROM pg_stat_activity;`
3. Load test with `ab -n 1000 -c 10 http://localhost:8000/`
4. Verify no connection errors

## Acceptance criteria
- [ ] Connections reused between requests
- [ ] No "too many connections" errors
- [ ] DB latency reduced by 20%+
- [ ] Pool size configurable via env

## Notes
- For Coolify deployment, check if PgBouncer is available
- Alternatively, use CONN_MAX_AGE + CONN_HEALTH_CHECKS
- Monitor `pg_stat_activity` for pool size tuning

Codeberg issue: #261
