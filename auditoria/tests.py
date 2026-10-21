"""
Tests del registro de actividad: qué acciones quedan registradas, con qué detalle,
quién puede consultarlo y que los registros no se puedan alterar.
"""

import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from noticias.models import Noticia
from sedes.models import Sede
from tramites_app.models import Tramite
from turnos.models import Turno
from usuarios.models import PerfilEmpleado
from .models import RegistroActividad

_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def proximo_dia_habil():
    feriados = ["01-01", "03-03", "03-04", "04-02", "05-01", "05-25",
                "06-20", "07-09", "08-17", "10-12", "11-20", "12-08", "12-25"]
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5 or f"{d.month:02d}-{d.day:02d}" in feriados:
        d += timedelta(days=1)
    return d


@override_settings(AXES_ENABLED=False, STORAGES=_STORAGES)
class RegistroActividadTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='sa@test.com', password='Clave-Admin-2026',
                                              first_name='Ana', last_name='Admin', is_staff=True)
        PerfilEmpleado.objects.create(user=self.admin, rol='super_admin')
        self.operador = User.objects.create_user(username='op@test.com', password='Clave-Oper-2026',
                                                 first_name='Oscar', last_name='Operador', is_staff=True)
        PerfilEmpleado.objects.create(user=self.operador, rol='operador')
        self.client.login(username='sa@test.com', password='Clave-Admin-2026')

    def _post(self, nombre_url, data, args=None):
        return self.client.post(reverse(nombre_url, args=args), data=json.dumps(data),
                                content_type='application/json')

    def ultimo(self):
        return RegistroActividad.objects.first()

    # ── Noticias ──
    def test_crear_editar_y_eliminar_noticia(self):
        self.client.post(reverse('api_crear_noticia'), {'titulo': 'Aviso', 'cuerpo': 'Texto', 'tag': 'General'})
        n = Noticia.objects.get()
        r = self.ultimo()
        self.assertEqual((r.accion, r.modulo, r.objeto, r.usuario), ('crear', 'noticias', 'Aviso', self.admin))
        self.assertEqual(r.usuario_nombre, 'Ana Admin')

        self.client.post(reverse('api_editar_noticia', args=[n.id]),
                         {'titulo': 'Aviso corregido', 'cuerpo': 'Texto', 'tag': 'General', 'estado': 'publicada'})
        r = self.ultimo()
        self.assertEqual(r.accion, 'editar')
        self.assertEqual(r.cambios['titulo'], ['Aviso', 'Aviso corregido'])
        self.assertEqual(r.cambios['estado'], ['borrador', 'publicada'])
        self.assertNotIn('cuerpo', r.cambios)   # solo lo que cambió

        self.client.post(reverse('api_eliminar_noticia', args=[n.id]))
        r = self.ultimo()
        self.assertEqual(r.accion, 'eliminar')
        self.assertEqual(r.cambios['titulo'], 'Aviso corregido')   # copia de lo eliminado

    def test_editar_sin_cambios_no_registra(self):
        self.client.post(reverse('api_crear_noticia'), {'titulo': 'Aviso', 'cuerpo': 'Texto', 'tag': 'General'})
        n = Noticia.objects.get()
        antes = RegistroActividad.objects.count()
        self.client.post(reverse('api_editar_noticia', args=[n.id]),
                         {'titulo': 'Aviso', 'cuerpo': 'Texto', 'tag': 'General', 'estado': 'borrador'})
        self.assertEqual(RegistroActividad.objects.count(), antes)

    # ── Trámites ──
    def test_tramite_creado_y_eliminado(self):
        self._post('api_crear_tramite', {'nombre': 'Partida', 'slug': 'partida'})
        t = Tramite.objects.get()
        self.assertEqual(self.ultimo().accion, 'crear')
        self.client.post(reverse('api_eliminar_tramite', args=[t.id]))
        r = self.ultimo()
        self.assertEqual((r.accion, r.cambios['slug']), ('eliminar', 'partida'))

    def test_editar_tramite_inexistente_da_404(self):
        self.assertEqual(self._post('api_editar_tramite', {'nombre': 'X'}, args=[999]).status_code, 404)

    # ── Sedes ──
    def test_cambio_de_ubicacion_y_sede_de_turnos_online(self):
        central = Sede.objects.create(nombre='Central', direccion='Entre Ríos 55', departamento='Capital',
                                      horario='L a V', latitud='-27.795100', longitud='-64.261500',
                                      activo=True, recibe_turnos_online=True)
        banda = Sede.objects.create(nombre='Banda', direccion='Malvinas 344', departamento='Banda',
                                    horario='L a V', latitud='-27.735', longitud='-64.243', activo=True)
        self._post('editar_sede', {'direccion': 'Andes y Belgrano Norte', 'lat': '-27.78384', 'lng': '-64.26695'},
                   args=[central.id])
        r = self.ultimo()
        self.assertEqual(r.cambios['direccion'], ['Entre Ríos 55', 'Andes y Belgrano Norte'])
        self.assertIn('latitud', r.cambios)

        self._post('editar_sede', {'recibe_turnos_online': True}, args=[banda.id])
        desmarcada = RegistroActividad.objects.filter(objeto='Central', accion='editar').first()
        self.assertEqual(desmarcada.cambios, {'recibe_turnos_online': [True, False]})

    # ── Usuarios ──
    def test_usuarios_sin_guardar_contrasenas(self):
        self._post('crear_usuario', {'nombre': 'Juan Pérez', 'email': 'juan@test.com',
                                     'password': 'Temporal-Entrega-01', 'rol': 'operador'})
        r = self.ultimo()
        self.assertEqual((r.accion, r.modulo), ('crear', 'usuarios'))
        self.assertNotIn('Temporal-Entrega-01', json.dumps(r.cambios))

        juan = User.objects.get(username='juan@test.com')
        self._post('editar_usuario', {'rol': 'super_admin', 'password': 'Blanqueo-Temporal-02'}, args=[juan.id])
        r = self.ultimo()
        self.assertEqual(r.cambios['rol'], ['operador', 'super_admin'])
        self.assertEqual(r.cambios['contraseña'][1], 'blanqueada (temporal)')
        self.assertNotIn('Blanqueo-Temporal-02', json.dumps(r.cambios))

        self.client.post(reverse('desactivar_usuario', args=[juan.id]))
        self.assertEqual(self.ultimo().accion, 'desactivar')

    # ── Turnos ──
    def test_turnos_manual_estado_y_reprogramacion(self):
        fecha = proximo_dia_habil()
        datos = {'tramite': 'dni-14', 'nombre': 'María González', 'dni': '30123456', 'email': 'maria@test.com',
                 'telefono': '3854111111', 'direccion': 'Libertad 200', 'fecha': fecha.isoformat(), 'hora': '09:00'}

        self.client.logout()
        self._post('api_crear_turno', datos)                       # ciudadano: no va a la bitácora
        self.assertFalse(RegistroActividad.objects.filter(modulo='turnos').exists())

        self.client.login(username='op@test.com', password='Clave-Oper-2026')
        self._post('api_crear_turno', {**datos, 'dni': '22333444', 'hora': '09:15', 'origen': 'manual'})
        r = self.ultimo()
        self.assertEqual((r.accion, r.modulo, r.usuario), ('crear', 'turnos', self.operador))

        turno = Turno.objects.get(dni='30123456')
        self._post('api_cambiar_estado', {'estado': 'cancelado'}, args=[turno.id])
        self.assertEqual(self.ultimo().cambios, {'estado': ['pendiente', 'cancelado']})

        self._post('api_reprogramar_turno', {'fecha': fecha.isoformat(), 'hora': '10:00'}, args=[turno.id])
        r = self.ultimo()
        self.assertEqual(r.accion, 'reprogramar')
        self.assertEqual(r.cambios['hora'], ['09:00', '10:00'])

    # ── Sesión ──
    def test_login_y_logout_quedan_registrados(self):
        self.client.logout()
        self.client.post(reverse('login'), {'username': 'op@test.com', 'password': 'Clave-Oper-2026'})
        self.assertEqual((self.ultimo().accion, self.ultimo().usuario), ('login', self.operador))
        self.client.post(reverse('logout'))
        self.assertEqual(self.ultimo().accion, 'logout')

    # ── Consulta y protección ──
    def test_solo_super_admin_consulta_el_registro(self):
        self.client.post(reverse('api_crear_noticia'), {'titulo': 'Aviso', 'cuerpo': 'Texto', 'tag': 'General'})
        r = self.client.get(reverse('api_actividad'), {'modulo': 'noticias'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['total'], 1)
        self.assertEqual(r.json()['registros'][0]['usuario'], 'Ana Admin')

        self.client.logout()
        self.client.login(username='op@test.com', password='Clave-Oper-2026')
        self.assertEqual(self.client.get(reverse('api_actividad')).status_code, 403)

    def test_los_registros_no_se_pueden_modificar_ni_borrar(self):
        self.client.post(reverse('api_crear_noticia'), {'titulo': 'Aviso', 'cuerpo': 'Texto', 'tag': 'General'})
        r = self.ultimo()
        r.objeto = 'otra cosa'
        with self.assertRaises(ValueError):
            r.save()
        with self.assertRaises(ValueError):
            r.delete()
