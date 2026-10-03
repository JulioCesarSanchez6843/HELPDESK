"""Configuración para desarrollo local (tu máquina)."""
from .base import *  # noqa

DEBUG = True

INSTALLED_APPS += [
    "django.contrib.admindocs",
]

AUTH_PASSWORD_VALIDATORS = []