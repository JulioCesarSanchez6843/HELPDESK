"""
Lógica de historial y notificaciones de los tickets,
en un solo lugar.

Las vistas solamente llaman a estas funciones
después de guardar los cambios correspondientes.
"""

from apps.accounts.models import Usuario

from .models import (
    Historial,
    Notificacion,
    Ticket,
)


def _admins_activos():
    """
    Obtiene todos los administradores activos.
    """

    return list(
        Usuario.objects.filter(
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
    )


def _notificar(
    destinatarios,
    tipo,
    mensaje,
    ticket,
    actor,
):
    """
    Crea una notificación por destinatario.

    No repite destinatarios y no le envía
    la notificación al usuario que realizó la acción.
    """

    unicos = {}

    for usuario in destinatarios:

        if (
            usuario
            and usuario.activo
            and usuario.pk != actor.pk
        ):
            unicos[usuario.pk] = usuario

    Notificacion.objects.bulk_create(
        [
            Notificacion(
                usuario=usuario,
                ticket=ticket,
                tipo=tipo,
                mensaje=mensaje,
            )
            for usuario in unicos.values()
        ]
    )


def registrar_creacion(ticket, autor):
    """
    Registra la creación del ticket
    y notifica a los ADMIN activos.
    """

    Historial.objects.create(
        ticket=ticket,
        usuario=autor,
        tipo=Historial.Tipo.CREACION,
        contenido="Ticket creado.",
    )

    _notificar(
        _admins_activos(),
        Notificacion.Tipo.NUEVO_TICKET,
        (
            f"Nuevo ticket #{ticket.pk}: "
            f"{ticket.titulo}"
        ),
        ticket,
        autor,
    )


def registrar_comentario(
    ticket,
    autor,
    texto,
):
    """
    Registra un comentario.

    Si comenta un ADMIN:
        → se notifica al usuario que creó el ticket.

    Si comenta un USUARIO:
        → se notifica a los ADMIN activos.
    """

    Historial.objects.create(
        ticket=ticket,
        usuario=autor,
        tipo=Historial.Tipo.COMENTARIO,
        contenido=texto,
    )

    if autor.es_admin:

        destinatarios = [
            ticket.creado_por
        ]

    else:

        destinatarios = _admins_activos()

    _notificar(
        destinatarios,
        Notificacion.Tipo.COMENTARIO,
        (
            f"{autor.nombre} comentó "
            f"en el ticket #{ticket.pk}."
        ),
        ticket,
        autor,
    )


def snapshot(ticket):
    """
    Obtiene una copia de los valores importantes
    del ticket antes de aplicar los cambios
    realizados por el ADMIN.
    """

    return {
        "estado": ticket.estado,
        "categoria_id": ticket.categoria_id,
    }


def registrar_gestion(
    ticket,
    actor,
    antes,
):
    """
    Compara el ticket actual contra el snapshot
    anterior y registra los cambios realizados
    por el ADMIN.
    """

    # ---------------------------------------------------------------
    # CAMBIO DE ESTADO
    # ---------------------------------------------------------------

    if ticket.estado != antes["estado"]:

        anterior = dict(
            Ticket.Estado.choices
        )[antes["estado"]]

        texto = (
            f"Estado cambiado de "
            f"«{anterior}» a "
            f"«{ticket.get_estado_display()}»."
        )

        cerrado = (
            ticket.estado
            == Ticket.Estado.CERRADO
        )

        if cerrado:
            texto += (
                f" Nota de resolución: "
                f"{ticket.nota_resolucion}"
            )

        Historial.objects.create(
            ticket=ticket,
            usuario=actor,
            tipo=Historial.Tipo.CAMBIO_ESTADO,
            contenido=texto,
        )

        if cerrado:

            _notificar(
                [ticket.creado_por],
                Notificacion.Tipo.TICKET_CERRADO,
                (
                    f"Tu ticket #{ticket.pk} "
                    f"fue cerrado."
                ),
                ticket,
                actor,
            )

        else:

            _notificar(
                [ticket.creado_por],
                Notificacion.Tipo.CAMBIO_ESTADO,
                (
                    f"Tu ticket #{ticket.pk} "
                    f"ahora está "
                    f"«{ticket.get_estado_display()}»."
                ),
                ticket,
                actor,
            )

    # ---------------------------------------------------------------
    # CAMBIO DE CATEGORÍA
    # ---------------------------------------------------------------

    if (
        ticket.categoria_id
        != antes["categoria_id"]
    ):

        nueva = (
            ticket.categoria.nombre
            if ticket.categoria
            else "Sin categoría"
        )

        Historial.objects.create(
            ticket=ticket,
            usuario=actor,
            tipo=Historial.Tipo.CATEGORIA,
            contenido=(
                f"Categoría cambiada a "
                f"«{nueva}»."
            ),
        )