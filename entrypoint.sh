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

# Start the web server and tasks worker
echo "Starting mprocs.."
exec mprocs -c /app/mprocs.yaml
