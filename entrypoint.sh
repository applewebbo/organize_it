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
    --port 80 \
    --interface wsgi \
    --no-ws \
    --loop uvloop \
    --process-name "granian [core]" \
    --workers 2 \
    --backlog 1024 \
    --backpressure 256
