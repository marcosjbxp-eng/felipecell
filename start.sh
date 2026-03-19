#!/bin/bash
echo ">> Rodando collectstatic..."
python manage.py collectstatic --noinput

echo ">> Rodando migrações..."
python manage.py migrate --noinput

echo ">> Iniciando gunicorn..."
python -m gunicorn core.wsgi:application --bind 0.0.0.0:80 --workers 2
