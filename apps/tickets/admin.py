from django.contrib import admin

from .models import Ticket, Historial, Notificacion


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "titulo",
        "estado",
        "area",
        "categoria",
        "creado_por",
        "creado_en",
        "cerrado_en",
    )

    list_filter = (
        "estado",
        "area",
        "categoria",
    )

    search_fields = (
        "titulo",
        "descripcion",
        "creado_por__nombre",
    )

    readonly_fields = (
        "creado_en",
        "cerrado_en",
    )


admin.site.register(Historial)

admin.site.register(Notificacion)