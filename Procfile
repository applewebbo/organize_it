web: gunicorn core.wsgi:application --bind=0.0.0.0:$PORT
worker: python manage.py qcluster
