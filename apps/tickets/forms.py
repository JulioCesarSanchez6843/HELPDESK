from django import forms
from django.utils import timezone

from apps.accounts.forms import BootstrapFormMixin
from .models import Ticket


class TicketForm(BootstrapFormMixin, forms.ModelForm):
    """Formulario de 'Nuevo ticket' que llena el usuario."""

    class Meta:
        model = Ticket

        fields = [
            "titulo",
            "area",
            "categoria",
            "numero_serie",
            "service_tag",
            "descripcion",
        ]

        labels = {
            "titulo": "Título",
            "area": "Área",
            "categoria": "Categoría",
            "descripcion": "Descripción",
            "numero_serie": "Número de serie",
            "service_tag": "Service tag",
        }

        help_texts = {
            "categoria": (
                "Opcional: el administrador puede asignarla después."
            ),
            "numero_serie": (
                "Opcional, si el problema es de un equipo."
            ),
            "service_tag": (
                "Opcional, si el problema es de un equipo."
            ),
        }

        widgets = {
            "descripcion": forms.Textarea(
                attrs={"rows": 4}
            )
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categoria"].required = False

        if (
            usuario is not None
            and usuario.area_id
            and not self.is_bound
        ):
            self.fields["area"].initial = usuario.area_id


class TicketGestionForm(
    BootstrapFormMixin,
    forms.ModelForm
):
    """Formulario que usa el ADMIN para atender el ticket."""

    class Meta:
        model = Ticket

        fields = [
            "estado",
            "categoria",
            "nota_resolucion",
        ]

        labels = {
            "estado": "Estado",
            "categoria": "Categoría",
            "nota_resolucion": "Nota de resolución",
        }

        help_texts = {
            "nota_resolucion": (
                "Obligatoria al cerrar el ticket. "
                "Si se vuelve a abrir, se borra."
            ),
        }

        widgets = {
            "nota_resolucion": forms.Textarea(
                attrs={"rows": 3}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categoria"].required = False

    def clean(self):
        datos = super().clean()

        cerrando = (
            datos.get("estado")
            == Ticket.Estado.CERRADO
        )

        nota = (
            datos.get("nota_resolucion") or ""
        ).strip()

        if cerrando and not nota:
            self.add_error(
                "nota_resolucion",
                (
                    "Escribe la nota de resolución "
                    "para cerrar el ticket."
                ),
            )

        # La nota solo existe en tickets cerrados.
        datos["nota_resolucion"] = (
            nota if cerrando else ""
        )

        return datos

    def save(self, commit=True):
        ticket = super().save(commit=False)

        if ticket.estado == Ticket.Estado.CERRADO:
            if ticket.cerrado_en is None:
                ticket.cerrado_en = timezone.now()
        else:
            ticket.cerrado_en = None

        if commit:
            ticket.save()

        return ticket


class ComentarioForm(forms.Form):
    comentario = forms.CharField(
        max_length=2000,
        strip=True,
    )