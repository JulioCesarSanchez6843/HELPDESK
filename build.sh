#!/usr/bin/env bash
# Script de construcción para Render: se ejecuta en cada despliegue.
set -o errexit

pip install -r requirements/prod.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Crea el administrador inicial, o le RESETEA la contraseña si ya existe,
# usando las variables de entorno de Render:
#   DJANGO_SUPERUSER_CORREO, DJANGO_SUPERUSER_NOMBRE, DJANGO_SUPERUSER_PASSWORD
if [[ -n "$DJANGO_SUPERUSER_CORREO" && -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
python manage.py shell <<'PYEOF'
import os
from django.contrib.auth import get_user_model

Usuario = get_user_model()
correo = os.environ["DJANGO_SUPERUSER_CORREO"].strip()
nombre = os.environ.get("DJANGO_SUPERUSER_NOMBRE", "Administrador")
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]

u = Usuario.objects.filter(correo__iexact=correo).first()
if u is None:
    Usuario.objects.create_superuser(correo, nombre, password)
    print(f"[build] Superusuario creado: {correo}")
else:
    u.set_password(password)
    u.is_staff = True
    u.is_superuser = True
    u.rol = "ADMIN"
    u.activo = True
    u.save()
    print(f"[build] Contraseña de {correo} actualizada")
PYEOF
else
  echo "[build] Falta DJANGO_SUPERUSER_CORREO o DJANGO_SUPERUSER_PASSWORD: no se crea admin"
fi