from django.conf import settings
from django.db import models
from django.utils import timezone


class Ticket(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CERRADO = "CERRADO", "Cerrado"

    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    numero_serie = models.CharField(max_length=50, blank=True)
    service_tag = models.CharField(max_length=50, blank=True)

    area = models.ForeignKey(
        "catalog.Area",
        on_delete=models.PROTECT,
        related_name="tickets",
    )

    categoria = models.ForeignKey(
        "catalog.Categoria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.ABIERTO,
    )

    nota_resolucion = models.TextField(blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_creados",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    cerrado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Ticket #{self.pk} - {self.titulo}"


class Historial(models.Model):
    """
    Registra cada evento importante del ticket:
    creación, comentarios, cambios de estado y cambios de categoría.
    """

    class Tipo(models.TextChoices):
        CREACION = "CREACION", "Creación"
        COMENTARIO = "COMENTARIO", "Comentario"
        CAMBIO_ESTADO = "CAMBIO_ESTADO", "Cambio de estado"
        CATEGORIA = "CATEGORIA", "Cambio de categoría"

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="historial",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    tipo = models.CharField(
        max_length=15,
        choices=Tipo.choices,
        default=Tipo.COMENTARIO,
    )

    contenido = models.TextField()

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name_plural = "Historial"

    def __str__(self):
        return (
            f"{self.get_tipo_display()} "
            f"en Ticket #{self.ticket_id} "
            f"por {self.usuario}"
        )


class Notificacion(models.Model):
    class Tipo(models.TextChoices):
        NUEVO_TICKET = "NUEVO_TICKET", "Nuevo ticket"
        CAMBIO_ESTADO = "CAMBIO_ESTADO", "Cambio de estado"
        COMENTARIO = "COMENTARIO", "Comentario"
        TICKET_CERRADO = "TICKET_CERRADO", "Ticket cerrado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
    )

    mensaje = models.TextField()

    leida = models.BooleanField(default=False)

    creada_en = models.DateTimeField(auto_now_add=True)

    leida_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-creada_en", "-id"]
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.get_tipo_display()} para {self.usuario}"

    def marcar_leida(self):
        if not self.leida:
            self.leida = True
            self.leida_en = timezone.now()
            self.save(
                update_fields=["leida", "leida_en"]
            )