MAIN=core/wsgi.py
MEMORY=512
VERSION=recommended
DISPLAY_NAME=Felipe Cell
DESCRIPTION=Aplicacao Django Felipe Cell
SUBDOMAIN=felipecell
START=gunicorn core.wsgi:application --bind 0.0.0.0:80 --workers 2
