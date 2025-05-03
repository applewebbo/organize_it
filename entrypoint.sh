#!/bin/sh

set -eu
export PYTHONWARNINGS="ignore::SyntaxWarning"

echo "Migrating Database..."
python manage.py migrate

echo "Translating..."
python manage.py compilemessages

echo "Building production css files..."
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting supervisord for granian and dbworker"
exec supervisord -c /app/supervisord.conf
