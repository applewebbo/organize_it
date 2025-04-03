#!/bin/sh

set -eu

# Check if uvloop is installed and set LOOP_ARG accordingly:
# - If uvloop exists: LOOP_ARG = "--loop uvloop"
# - If uvloop missing: LOOP_ARG = "" (empty string)
if ! python -c "import uvloop" 2>/dev/null; then
    echo "Warning: uvloop not found, falling back to default event loop"
    LOOP_ARG=""
else
    LOOP_ARG="--loop uvloop"
fi

echo "Migrating Database..."
python manage.py migrate

echo "Building production css files..."
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting granian..."
exec granian "core.wsgi:application" \
    --host 0.0.0.0 \
    --port 80 \
    --interface wsgi \
    --no-ws \
    ${LOOP_ARG} \
    --process-name "granian [core]" \
    --workers 2 \
    --threads 16 \
    --backlog 1024 \
    --backpressure 512 \
    --thread-stack-size 131072 \
    --max-requests 500 \
    --max-requests-jitter 50 \
    --keep-alive 65 \
    --graceful-timeout 30
