from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    """Manager personalizado: Django necesita este código para saber
    cómo crear usuarios normales y superusuarios usando 'correo' en vez
    de 'username'."""

    def get_by_natural_key(self, correo):
        # El login no distingue mayúsculas/minúsculas en el correo.
        return self.get(correo__iexact=correo)

    def create_user(self, correo, nombre, password=None, **extra_fields):
        if not correo:
            raise ValueError("El correo es obligatorio")
        correo = self.normalize_email(correo)
        usuario = self.model(correo=correo, nombre=nombre, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, nombre, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("rol", "ADMIN")
        return self.create_user(correo, nombre, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        USUARIO = "USUARIO", "Usuario"

    nombre = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.USUARIO)
    puesto = models.ForeignKey(
        "catalog.Puesto", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="usuarios"
    )
    area = models.ForeignKey(
        "catalog.Area", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="usuarios"
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)  # necesario para entrar a /admin/

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre"]

    objects = UsuarioManager()

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def is_active(self):
        return self.activo

    @property
    def es_admin(self):
        # Un superusuario siempre cuenta como administrador de la app.
        return self.rol == self.Rol.ADMIN or self.is_superuser
