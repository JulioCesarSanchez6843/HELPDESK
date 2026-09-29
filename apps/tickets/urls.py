from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.lista_tickets,
        name="lista_tickets",
    ),

    path(
        "nuevo/",
        views.nuevo_ticket,
        name="nuevo_ticket",
    ),

    # Las rutas de notificaciones van antes de <int:pk>
    # para evitar conflictos con la ruta del detalle del ticket.
    path(
        "notificaciones/",
        views.lista_notificaciones,
        name="lista_notificaciones",
    ),

    path(
        "notificaciones/leer-todas/",
        views.notificaciones_leer_todas,
        name="notificaciones_leer_todas",
    ),

    path(
        "notificaciones/<int:pk>/abrir/",
        views.abrir_notificacion,
        name="abrir_notificacion",
    ),

    path(
        "notificaciones/<int:pk>/leer/",
        views.marcar_notificacion_leida,
        name="marcar_notificacion_leida",
    ),

    path(
        "<int:pk>/",
        views.detalle_ticket,
        name="detalle_ticket",
    ),
]