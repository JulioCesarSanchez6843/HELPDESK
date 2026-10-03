from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.catalog.models import Area, Categoria

from . import services
from .forms import (
    ComentarioForm,
    TicketForm,
    TicketGestionForm,
)
from .models import Ticket


ESTADOS_VALIDOS = {
    valor
    for valor, _ in Ticket.Estado.choices
}

TICKETS_POR_PAGINA = 15


def _tickets_visibles(usuario):
    """
    El ADMIN ve todos los tickets.
    El USUARIO solamente ve los tickets que él creó.
    """

    tickets = Ticket.objects.select_related(
        "area",
        "categoria",
        "creado_por",
    )

    if usuario.es_admin:
        return tickets

    return tickets.filter(
        creado_por=usuario
    )


@login_required
def lista_tickets(request):
    """
    Pantalla 'Panel de administración' para ADMIN
    o 'Mis Tickets' para USUARIO.
    """

    es_admin = request.user.es_admin
    base = _tickets_visibles(request.user)

    conteos = base.aggregate(
        total=Count("id"),
        abiertos=Count(
            "id",
            filter=Q(
                estado=Ticket.Estado.ABIERTO
            ),
        ),
        en_proceso=Count(
            "id",
            filter=Q(
                estado=Ticket.Estado.EN_PROCESO
            ),
        ),
        cerrados=Count(
            "id",
            filter=Q(
                estado=Ticket.Estado.CERRADO
            ),
        ),
    )

    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    area = request.GET.get("area", "")
    categoria = request.GET.get("categoria", "")

    tickets = base

    if q:
        filtro = Q(
            titulo__icontains=q
        )

        if es_admin:
            filtro |= Q(
                creado_por__nombre__icontains=q
            )

        tickets = tickets.filter(filtro)

    if estado in ESTADOS_VALIDOS:
        tickets = tickets.filter(
            estado=estado
        )
    else:
        estado = ""

    if es_admin and area.isdigit():
        tickets = tickets.filter(
            area_id=int(area)
        )
    else:
        area = ""

    if es_admin and categoria.isdigit():
        tickets = tickets.filter(
            categoria_id=int(categoria)
        )
    else:
        categoria = ""

    pagina = Paginator(
        tickets,
        TICKETS_POR_PAGINA,
    ).get_page(
        request.GET.get("page")
    )

    parametros = request.GET.copy()
    parametros.pop("page", None)

    contexto = {
        "page_obj": pagina,
        "conteos": conteos,
        "q": q,
        "estado_sel": estado,
        "area_sel": area,
        "categoria_sel": categoria,
        "estados": Ticket.Estado.choices,
        "querystring": parametros.urlencode(),
    }

    if es_admin:
        contexto["areas"] = Area.objects.all()
        contexto["categorias"] = Categoria.objects.all()
        plantilla = "tickets/panel_admin.html"
    else:
        plantilla = "tickets/mis_tickets.html"

    return render(
        request,
        plantilla,
        contexto,
    )


@login_required
def detalle_ticket(request, pk):
    """
    Muestra el detalle de un ticket.

    Un usuario normal solamente puede abrir
    sus propios tickets.
    El ADMIN puede abrir cualquier ticket.
    """

    ticket = get_object_or_404(
        _tickets_visibles(request.user),
        pk=pk,
    )

    es_admin = request.user.es_admin

    form_gestion = (
        TicketGestionForm(instance=ticket)
        if es_admin
        else None
    )

    form_comentario = ComentarioForm()

    if request.method == "POST":

        if "guardar_gestion" in request.POST:

            if not es_admin:
                raise PermissionDenied

            antes = services.snapshot(ticket)

            instancia = Ticket.objects.get(
                pk=ticket.pk
            )

            form_gestion = TicketGestionForm(
                request.POST,
                instance=instancia,
            )

            if form_gestion.is_valid():

                with transaction.atomic():

                    form_gestion.save()

                    instancia.refresh_from_db()

                    services.registrar_gestion(
                        instancia,
                        request.user,
                        antes,
                    )

                messages.success(
                    request,
                    "Ticket actualizado.",
                )

                return redirect(
                    "detalle_ticket",
                    pk=pk,
                )

        elif "comentario" in request.POST:

            form_comentario = ComentarioForm(
                request.POST
            )

            if form_comentario.is_valid():

                with transaction.atomic():

                    services.registrar_comentario(
                        ticket,
                        request.user,
                        form_comentario.cleaned_data[
                            "comentario"
                        ],
                    )

                return redirect(
                    "detalle_ticket",
                    pk=pk,
                )

    return render(
        request,
        "tickets/detalle_ticket.html",
        {
            "ticket": ticket,
            "historial": (
                ticket.historial
                .select_related("usuario")
            ),
            "form_gestion": form_gestion,
            "form_comentario": form_comentario,
        },
    )


@login_required
def nuevo_ticket(request):

    if request.method == "POST":

        form = TicketForm(
            request.POST,
            usuario=request.user,
        )

        if form.is_valid():

            with transaction.atomic():

                ticket = form.save(
                    commit=False
                )

                ticket.creado_por = request.user
                ticket.save()

                services.registrar_creacion(
                    ticket,
                    request.user,
                )

            messages.success(
                request,
                "Ticket creado correctamente.",
            )

            return redirect(
                "detalle_ticket",
                pk=ticket.pk,
            )

    else:
        form = TicketForm(
            usuario=request.user
        )

    return render(
        request,
        "tickets/nuevo_ticket.html",
        {
            "form": form
        },
    )

@login_required
def lista_notificaciones(request):

    notificaciones = (
        request.user.notificaciones
        .select_related("ticket")[:50]
    )

    return render(
        request,
        "tickets/notificaciones.html",
        {
            "notificaciones": notificaciones
        },
    )


@login_required
@require_POST
def abrir_notificacion(request, pk):
    """
    Marca la notificación como leída.

    Si la notificación está relacionada con un ticket,
    abre el detalle de ese ticket.

    Si no está relacionada con ningún ticket,
    regresa a la lista de notificaciones.
    """

    notificacion = get_object_or_404(
        request.user.notificaciones,
        pk=pk,
    )

    notificacion.marcar_leida()

    # Si NO hay ticket relacionado,
    # simplemente vuelve a las notificaciones.
    if notificacion.ticket_id is None:
        return redirect(
            "lista_notificaciones"
        )

    # Si SÍ hay ticket, abre su detalle.
    return redirect(
        "detalle_ticket",
        pk=notificacion.ticket_id,
    )


@login_required
@require_POST
def marcar_notificacion_leida(request, pk):

    notificacion = get_object_or_404(
        request.user.notificaciones,
        pk=pk,
    )

    notificacion.marcar_leida()

    return redirect(
        "lista_notificaciones"
    )


@login_required
@require_POST
def notificaciones_leer_todas(request):

    request.user.notificaciones.filter(
        leida=False
    ).update(
        leida=True,
        leida_en=timezone.now(),
    )

    return redirect(
        "lista_notificaciones"
    )