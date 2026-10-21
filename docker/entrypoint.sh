#!/bin/sh
# Arranque del contenedor: aplica migraciones y levanta Gunicorn.
set -e

python manage.py migrate --noinput

exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
