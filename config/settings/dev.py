"""Configuración para desarrollo local (tu máquina)."""
from .base import *  # noqa

DEBUG = True

INSTALLED_APPS += [
    "django.contrib.admindocs",
]

# Validadores de contraseña relajados SOLO para desarrollo/pruebas
AUTH_PASSWORD_VALIDATORS = []