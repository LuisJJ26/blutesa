#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py sembrar_datos

exec python manage.py runserver 0.0.0.0:8030
