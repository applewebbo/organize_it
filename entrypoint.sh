#!/bin/sh

set -eu
export PYTHONWARNINGS="ignore::SyntaxWarning"

echo "Migrating Database..."
python manage.py migrate

echo "Translating..."
python manage.py compilemessages -l it -l en

# Start the web server and tasks worker
echo "Starting hivemind.."
exec hivemind /app/Procfile
