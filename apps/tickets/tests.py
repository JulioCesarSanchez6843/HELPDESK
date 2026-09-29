from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.catalog.models import Area, Categoria

from .models import Historial, Notificacion, Ticket


PASSWORD = "pw-segura-123"


class BaseTicketsTest(TestCase):
    def setUp(self):
        self.area = Area.objects.create(
            nombre="Contabilidad"
        )

        self.categoria = Categoria.objects.create(
            nombre="Red"
        )

        self.admin = Usuario.objects.create_user(
            "admin@t.com",
            "Admin",
            PASSWORD,
            rol=Usuario.Rol.ADMIN,
            area=self.area,
        )

        self.admin2 = Usuario.objects.create_user(
            "admin2@t.com",
            "Admin Dos",
            PASSWORD,
            rol=Usuario.Rol.ADMIN,
            area=self.area,
        )

        self.u1 = Usuario.objects.create_user(
            "u1@t.com",
            "Usuario Uno",
            PASSWORD,
            area=self.area,
        )

        self.u2 = Usuario.objects.create_user(
            "u2@t.com",
            "Usuario Dos",
            PASSWORD,
            area=self.area,
        )

    def entrar(self, usuario):
        self.client.force_login(usuario)

    def crear_ticket(self, autor=None, **extra):
        datos = {
            "titulo": "Falla de red",
            "descripcion": "No hay internet",
            "area": self.area,
            "creado_por": autor or self.u1,
        }

        datos.update(extra)

        return Ticket.objects.create(**datos)

    def gestionar(self, ticket, **campos):
        datos = {
            "guardar_gestion": "1",
            "estado": ticket.estado,
            "categoria": "",
            "nota_resolucion": "",
        }

        datos.update(campos)

        return self.client.post(
            reverse(
                "detalle_ticket",
                args=[ticket.pk],
            ),
            datos,
        )


class CreacionTicketTests(BaseTicketsTest):

    def test_usuario_crea_ticket_con_estado_historial_y_notifica_admins(self):
        self.entrar(self.u1)

        r = self.client.post(
            reverse("nuevo_ticket"),
            {
                "titulo": "No imprime",
                "area": self.area.pk,
                "categoria": "",
                "descripcion": "La impresora no responde",
                "numero_serie": "SN123",
                "service_tag": "TAG9",
            },
        )

        ticket = Ticket.objects.get()

        self.assertRedirects(
            r,
            reverse(
                "detalle_ticket",
                args=[ticket.pk],
            ),
        )

        self.assertEqual(
            ticket.estado,
            Ticket.Estado.ABIERTO,
        )

        self.assertEqual(
            ticket.creado_por,
            self.u1,
        )

        self.assertEqual(
            (
                ticket.numero_serie,
                ticket.service_tag,
            ),
            (
                "SN123",
                "TAG9",
            ),
        )

        self.assertEqual(
            ticket.historial.get().tipo,
            Historial.Tipo.CREACION,
        )

        destinatarios = set(
            Notificacion.objects.values_list(
                "usuario_id",
                flat=True,
            )
        )

        self.assertEqual(
            destinatarios,
            {
                self.admin.pk,
                self.admin2.pk,
            },
        )

    def test_el_area_del_usuario_viene_preseleccionada(self):
        self.entrar(self.u1)

        r = self.client.get(
            reverse("nuevo_ticket")
        )

        self.assertEqual(
            r.context["form"].fields["area"].initial,
            self.area.pk,
        )


class PermisosTicketsTests(BaseTicketsTest):

    def test_usuario_no_ve_ni_comenta_tickets_ajenos(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        self.entrar(self.u2)

        url = reverse(
            "detalle_ticket",
            args=[ticket.pk],
        )

        self.assertEqual(
            self.client.get(url).status_code,
            404,
        )

        self.assertEqual(
            self.client.post(
                url,
                {
                    "comentario": "hola"
                },
            ).status_code,
            404,
        )

        self.assertEqual(
            Historial.objects.filter(
                usuario=self.u2
            ).count(),
            0,
        )

    def test_lista_de_usuario_solo_muestra_sus_tickets(self):
        propio = self.crear_ticket(
            autor=self.u1,
            titulo="Mio",
        )

        ajeno = self.crear_ticket(
            autor=self.u2,
            titulo="Ajeno",
        )

        self.entrar(self.u1)

        r = self.client.get(
            reverse("lista_tickets")
        )

        self.assertContains(
            r,
            propio.titulo,
        )

        self.assertNotContains(
            r,
            ajeno.titulo,
        )

    def test_usuario_no_puede_gestionar_ticket(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        self.entrar(self.u1)

        r = self.gestionar(
            ticket,
            estado="CERRADO",
            nota_resolucion="x",
        )

        self.assertEqual(
            r.status_code,
            403,
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.estado,
            Ticket.Estado.ABIERTO,
        )

    def test_admin_ve_todos_los_tickets(self):
        t1 = self.crear_ticket(
            autor=self.u1,
            titulo="Ticket Usuario Uno",
        )

        t2 = self.crear_ticket(
            autor=self.u2,
            titulo="Ticket Usuario Dos",
        )

        self.entrar(self.admin)

        r = self.client.get(
            reverse("lista_tickets")
        )

        self.assertContains(
            r,
            t1.titulo,
        )

        self.assertContains(
            r,
            t2.titulo,
        )


class GestionTicketsTests(BaseTicketsTest):

    def test_cerrar_exige_nota_de_resolucion(self):
        ticket = self.crear_ticket()

        self.entrar(self.admin)

        r = self.gestionar(
            ticket,
            estado="CERRADO",
            nota_resolucion="   ",
        )

        self.assertEqual(
            r.status_code,
            200,
        )

        self.assertIn(
            "nota_resolucion",
            r.context["form_gestion"].errors,
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.estado,
            Ticket.Estado.ABIERTO,
        )

        self.assertIsNone(
            ticket.cerrado_en
        )

    def test_cerrar_guarda_fecha_nota_historial_y_notifica_al_creador(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        self.entrar(self.admin)

        r = self.gestionar(
            ticket,
            estado="CERRADO",
            nota_resolucion="Se cambió el cable",
        )

        self.assertEqual(
            r.status_code,
            302,
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.estado,
            Ticket.Estado.CERRADO,
        )

        self.assertIsNotNone(
            ticket.cerrado_en
        )

        self.assertEqual(
            ticket.nota_resolucion,
            "Se cambió el cable",
        )

        evento = ticket.historial.get(
            tipo=Historial.Tipo.CAMBIO_ESTADO
        )

        self.assertIn(
            "Se cambió el cable",
            evento.contenido,
        )

        n = Notificacion.objects.get(
            usuario=self.u1
        )

        self.assertEqual(
            n.tipo,
            Notificacion.Tipo.TICKET_CERRADO,
        )

    def test_reabrir_limpia_fecha_de_cierre_y_nota(self):
        ticket = self.crear_ticket(
            estado="CERRADO",
            nota_resolucion="ok",
            cerrado_en=timezone.now(),
        )

        self.entrar(self.admin)

        self.gestionar(
            ticket,
            estado="EN_PROCESO",
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.estado,
            Ticket.Estado.EN_PROCESO,
        )

        self.assertIsNone(
            ticket.cerrado_en
        )

        self.assertEqual(
            ticket.nota_resolucion,
            "",
        )

    def test_cambio_de_categoria_y_estado_quedan_en_historial(self):
        ticket = self.crear_ticket()

        self.entrar(self.admin)

        self.gestionar(
            ticket,
            estado="EN_PROCESO",
            categoria=self.categoria.pk,
        )

        tipos = set(
            ticket.historial.values_list(
                "tipo",
                flat=True,
            )
        )

        self.assertEqual(
            tipos,
            {
                Historial.Tipo.CAMBIO_ESTADO,
                Historial.Tipo.CATEGORIA,
            },
        )

    def test_guardar_sin_cambios_no_genera_historial(self):
        ticket = self.crear_ticket()

        self.entrar(self.admin)

        self.gestionar(ticket)

        self.assertEqual(
            ticket.historial.count(),
            0,
        )


class ComentariosYNotificacionesTests(BaseTicketsTest):

    def test_comentario_del_usuario_avisa_a_los_admins(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        self.entrar(self.u1)

        self.client.post(
            reverse(
                "detalle_ticket",
                args=[ticket.pk],
            ),
            {
                "comentario": "¿Hay novedades?"
            },
        )

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.historial.get().tipo,
            Historial.Tipo.COMENTARIO,
        )

        destinatarios = set(
            Notificacion.objects.values_list(
                "usuario_id",
                flat=True,
            )
        )

        self.assertEqual(
            destinatarios,
            {
                self.admin.pk,
                self.admin2.pk,
            },
        )

    def test_comentario_del_admin_avisa_al_creador_y_no_a_si_mismo(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        self.entrar(self.admin)

        self.client.post(
            reverse(
                "detalle_ticket",
                args=[ticket.pk],
            ),
            {
                "comentario": "Revisando"
            },
        )

        destinatarios = list(
            Notificacion.objects.values_list(
                "usuario_id",
                flat=True,
            )
        )

        self.assertEqual(
            destinatarios,
            [self.u1.pk],
        )

    def test_comentario_vacio_se_rechaza(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        self.entrar(self.u1)

        self.client.post(
            reverse(
                "detalle_ticket",
                args=[ticket.pk],
            ),
            {
                "comentario": "   "
            },
        )

        self.assertEqual(
            ticket.historial.count(),
            0,
        )

    def test_marcar_leida_y_abrir_notificacion(self):
        ticket = self.crear_ticket(
            autor=self.u1
        )

        n = Notificacion.objects.create(
            usuario=self.u1,
            ticket=ticket,
            tipo=Notificacion.Tipo.COMENTARIO,
            mensaje="m",
        )

        self.entrar(self.u1)

        r = self.client.post(
            reverse(
                "abrir_notificacion",
                args=[n.pk],
            )
        )

        self.assertRedirects(
            r,
            reverse(
                "detalle_ticket",
                args=[ticket.pk],
            ),
        )

        n.refresh_from_db()

        self.assertTrue(
            n.leida
        )

        self.assertIsNotNone(
            n.leida_en
        )

    def test_no_se_puede_tocar_notificacion_de_otro(self):
        n = Notificacion.objects.create(
            usuario=self.u1,
            tipo=Notificacion.Tipo.COMENTARIO,
            mensaje="m",
        )

        self.entrar(self.u2)

        self.assertEqual(
            self.client.post(
                reverse(
                    "marcar_notificacion_leida",
                    args=[n.pk],
                )
            ).status_code,
            404,
        )

    def test_leer_todas_y_contador_en_el_menu(self):
        for _ in range(3):
            Notificacion.objects.create(
                usuario=self.u1,
                tipo=Notificacion.Tipo.COMENTARIO,
                mensaje="m",
            )

        self.entrar(self.u1)

        r = self.client.get(
            reverse("lista_notificaciones")
        )

        self.assertEqual(
            r.context["notificaciones_sin_leer"],
            3,
        )

        self.client.post(
            reverse(
                "notificaciones_leer_todas"
            )
        )

        r = self.client.get(
            reverse("lista_notificaciones")
        )

        self.assertEqual(
            r.context["notificaciones_sin_leer"],
            0,
        )


class FiltrosTests(BaseTicketsTest):

    def test_busqueda_y_filtros_del_panel(self):
        self.crear_ticket(
            autor=self.u1,
            titulo="Impresora rota",
            categoria=self.categoria,
        )

        otro = self.crear_ticket(
            autor=self.u2,
            titulo="Excel se cierra",
            estado="CERRADO",
        )

        self.entrar(self.admin)

        url = reverse(
            "lista_tickets"
        )

        self.assertEqual(
            self.client.get(
                url,
                {"q": "impresora"},
            ).context["page_obj"].paginator.count,
            1,
        )

        self.assertEqual(
            self.client.get(
                url,
                {"q": otro.titulo},
            ).context["page_obj"].paginator.count,
            1,
        )

        self.assertEqual(
            self.client.get(
                url,
                {"q": "Usuario Dos"},
            ).context["page_obj"].paginator.count,
            1,
        )

        self.assertEqual(
            self.client.get(
                url,
                {"estado": "CERRADO"},
            ).context["page_obj"].paginator.count,
            1,
        )

        self.assertEqual(
            self.client.get(
                url,
                {"categoria": self.categoria.pk},
            ).context["page_obj"].paginator.count,
            1,
        )

        self.assertEqual(
            self.client.get(
                url,
                {"area": self.area.pk},
            ).context["page_obj"].paginator.count,
            2,
        )

    def test_parametros_invalidos_no_rompen_la_pagina(self):
        self.entrar(self.admin)

        r = self.client.get(
            reverse("lista_tickets"),
            {
                "estado": "XX",
                "area": "abc",
                "categoria": "1;drop",
                "page": "zzz",
            },
        )

        self.assertEqual(
            r.status_code,
            200,
        )

    def test_conteos_ignoran_los_filtros(self):
        self.crear_ticket()

        self.crear_ticket(
            estado="CERRADO"
        )

        self.entrar(self.admin)

        r = self.client.get(
            reverse("lista_tickets"),
            {
                "estado": "CERRADO"
            },
        )

        self.assertEqual(
            r.context["conteos"]["total"],
            2,
        )