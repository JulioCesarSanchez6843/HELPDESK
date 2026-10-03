#!/usr/bin/env bash
# Script de construcción para Render: se ejecuta en cada despliegue.
set -o errexit

pip install -r requirements/prod.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Crea el administrador inicial si no existe (usa las variables
# DJANGO_SUPERUSER_CORREO, DJANGO_SUPERUSER_NOMBRE y DJANGO_SUPERUSER_PASSWORD).
if [[ -n "$DJANGO_SUPERUSER_CORREO" ]]; then
  python manage.py createsuperuser --no-input || true
fi
