#!/bin/bash
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python -m gunicorn core.wsgi:application --bind 0.0.0.0:80 --workers 2
