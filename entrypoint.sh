#!/bin/bash
set -e

uv run python manage.py migrate --noinput

uv run python manage.py collectstatic --noinput || true

uv run python manage.py compilemessages

exec uv run gunicorn -w ${GUNICORN_WORKERS:-3} config.wsgi:application \
    --bind 0.0.0.0:${DJANGO_PORT:-8000} \
    --access-logfile - \
    --error-logfile - \
    --capture-output
