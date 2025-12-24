web: granian core.wsgi:application --host 0.0.0.0 --port 80 --interface wsgi --no-ws --loop uvloop --process-name "granian [core]" --workers 2 --backpressure 16
worker: python manage.py qcluster
