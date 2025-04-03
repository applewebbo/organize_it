#!/bin/sh

set -eu
export PYTHONWARNINGS="ignore::SyntaxWarning"

echo "Migrating Database..."
python manage.py migrate

echo "Building production css files..."
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting granian..."
exec granian "core.wsgi:application" \
    --host 0.0.0.0 \
    --port 8000 \
    --interface wsgi \
    --no-ws \
    --loop uvloop \
    --process-name "granian [core]" \
    --workers 2 \
    --backpressure 16 \
    --memory-target 256
