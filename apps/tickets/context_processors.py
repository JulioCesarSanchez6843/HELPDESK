def notificaciones(request):
    """Pone el contador de notificaciones sin leer en todas las plantillas (campana del menú)."""
    if request.user.is_authenticated:
        return {
            "notificaciones_sin_leer": request.user.notificaciones.filter(leida=False).count()
        }
    return {}
