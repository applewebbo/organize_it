#!/bin/sh

python manage.py collectstatic --noinput
python manage.py migrate
gunicorn core.wsgi:application --bind=0.0.0.0:80
