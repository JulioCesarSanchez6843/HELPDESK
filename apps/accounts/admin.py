from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("nombre",)
    list_display = ("nombre", "correo", "rol", "activo", "is_staff")
    list_filter = ("rol", "activo", "is_staff")
    search_fields = ("nombre", "correo")

    fieldsets = (
        (None, {"fields": ("correo", "password")}),
        ("Información personal", {"fields": ("nombre", "rol", "puesto", "area")}),
        ("Permisos", {"fields": ("activo", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas importantes", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("correo", "nombre", "rol", "area", "puesto", "password1", "password2"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")


admin.site.register(Usuario, UsuarioAdmin)
