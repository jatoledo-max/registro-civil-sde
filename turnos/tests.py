"""
Tests para la app 'turnos'.
Cubre: disponibilidad de slots, creación de turnos, correos y reprogramación.

Ejecutar con:
    python manage.py test turnos
"""

import json
from datetime import date, timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from .models import Turno


def proximo_dia_habil():
    """Devuelve el próximo día hábil (lunes a viernes, no feriado)."""
    FERIADOS = [
        "01-01","03-03","03-04","04-02","05-01","05-25",
        "06-20","07-09","08-17","10-12","11-20","12-08","12-25"
    ]
    d = date.today() + timedelta(days=1)
    while True:
        if d.weekday() < 5 and f"{d.month:02d}-{d.day:02d}" not in FERIADOS:
            return d
        d += timedelta(days=1)


def proximo_fin_de_semana():
    """Devuelve el próximo sábado."""
    d = date.today() + timedelta(days=1)
    while d.weekday() != 5:
        d += timedelta(days=1)
    return d


class DisponibilidadTests(TestCase):
    """Pruebas del endpoint público GET /api/turnos/disponibilidad/."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('api_disponibilidad')
        self.fecha_habil = proximo_dia_habil().isoformat()
        self.fecha_fin_semana = proximo_fin_de_semana().isoformat()

    def test_error_si_falta_parametro_fecha(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_error_si_formato_de_fecha_invalido(self):
        response = self.client.get(self.url, {'fecha': '30-06-2026'})
        self.assertEqual(response.status_code, 400)

    def test_fin_de_semana_no_es_habil(self):
        response = self.client.get(self.url, {'fecha': self.fecha_fin_semana})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['habil'])
        self.assertEqual(data['slots'], [])

    def test_fecha_pasada_no_es_habil(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.get(self.url, {'fecha': ayer})
        data = response.json()
        self.assertFalse(data['habil'])

    def test_dia_habil_retorna_slots(self):
        response = self.client.get(self.url, {'fecha': self.fecha_habil})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['habil'])
        self.assertIsInstance(data['slots'], list)
        self.assertGreater(len(data['slots']), 0)

    def test_slots_tienen_campos_esperados(self):
        response = self.client.get(self.url, {'fecha': self.fecha_habil})
        data = response.json()
        slot = data['slots'][0]
        self.assertIn('hora', slot)
        self.assertIn('libres', slot)
        self.assertIn('lleno', slot)

    def test_slot_ocupado_aparece_como_lleno(self):
        """Después de crear un turno, el slot debe aparecer como lleno."""
        fecha = proximo_dia_habil()
        Turno.objects.create(
            tramite='dni-nuevo',
            nombre='Juan Pérez',
            dni='12345678',
            email='juan@test.com',
            telefono='3814000000',
            direccion='Av. Belgrano 100',
            fecha=fecha,
            hora='10:00',
            estado='pendiente',
        )
        response = self.client.get(self.url, {'fecha': fecha.isoformat()})
        data = response.json()
        slot_10 = next((s for s in data['slots'] if s['hora'] == '10:00'), None)
        self.assertIsNotNone(slot_10)
        self.assertTrue(slot_10['lleno'])


class CrearTurnoTests(TestCase):
    """Pruebas del endpoint público POST /api/turnos/crear/."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('api_crear_turno')
        self.fecha_habil = proximo_dia_habil().isoformat()
        self.datos_validos = {
            'tramite':   'dni-nuevo',
            'nombre':    'María González',
            'dni':       '30123456',
            'email':     'maria@test.com',
            'telefono':  '3814111111',
            'direccion': 'Av. Libertad 200',
            'fecha':     self.fecha_habil,
            'hora':      '09:00',
        }

    def _post(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_crea_turno_con_datos_validos(self):
        response = self._post(self.datos_validos)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertIn('numero_turno', data)

    def test_turno_queda_guardado_en_base_de_datos(self):
        self._post(self.datos_validos)
        self.assertEqual(Turno.objects.filter(email='maria@test.com').count(), 1)

    def test_error_si_faltan_campos(self):
        datos_incompletos = {'nombre': 'Solo Nombre', 'email': 'x@x.com'}
        response = self._post(datos_incompletos)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_error_si_fecha_no_es_habil(self):
        datos = {**self.datos_validos, 'fecha': proximo_fin_de_semana().isoformat()}
        response = self._post(datos)
        self.assertEqual(response.status_code, 400)

    def test_error_si_hora_invalida(self):
        """Hora fuera del rango 09:00-12:45 debe ser rechazada."""
        datos = {**self.datos_validos, 'hora': '13:00'}
        response = self._post(datos)
        self.assertEqual(response.status_code, 400)

    def test_error_si_slot_ya_ocupado(self):
        """No se pueden crear dos turnos en el mismo slot."""
        self._post(self.datos_validos)
        datos2 = {**self.datos_validos, 'email': 'otro@test.com', 'dni': '99999999'}
        response = self._post(datos2)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_turno_tiene_estado_pendiente_por_defecto(self):
        self._post(self.datos_validos)
        turno = Turno.objects.get(email='maria@test.com')
        self.assertEqual(turno.estado, 'pendiente')

    def test_endpoint_es_publico_no_requiere_login(self):
        """Cualquier ciudadano puede crear un turno sin autenticarse."""
        response = self._post(self.datos_validos)
        self.assertNotEqual(response.status_code, 302)
        self.assertEqual(response.status_code, 200)

    def test_envia_correo_de_confirmacion(self):
        self._post(self.datos_validos)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('confirmado', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['maria@test.com'])

    def test_error_si_dni_invalido(self):
        for dni in ['123', '123456789', '30.12a.456']:
            response = self._post({**self.datos_validos, 'dni': dni})
            self.assertEqual(response.status_code, 400, dni)

    def test_acepta_dni_con_puntos(self):
        response = self._post({**self.datos_validos, 'dni': '30.123.456'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Turno.objects.get().dni, '30123456')

    def test_error_si_email_invalido(self):
        response = self._post({**self.datos_validos, 'email': 'maria@test'})
        self.assertEqual(response.status_code, 400)

    def test_error_si_nombre_invalido(self):
        for nombre in ['María', 'Mar1a González', 'X Y' * 60]:
            response = self._post({**self.datos_validos, 'nombre': nombre})
            self.assertEqual(response.status_code, 400, nombre)

    def test_error_si_telefono_invalido(self):
        for tel in ['123', 'abc1234567', '38541234567890']:
            response = self._post({**self.datos_validos, 'telefono': tel})
            self.assertEqual(response.status_code, 400, tel)

    def test_error_si_tramite_inexistente(self):
        response = self._post({**self.datos_validos, 'tramite': 'licencia'})
        self.assertEqual(response.status_code, 400)

    def test_error_si_json_invalido(self):
        response = self.client.post(self.url, data='no-json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_mismo_dni_no_puede_sacar_dos_turnos_el_mismo_dia(self):
        self._post(self.datos_validos)
        response = self._post({**self.datos_validos, 'hora': '09:15'})
        self.assertEqual(response.status_code, 400)

    def test_ciudadano_no_puede_elegir_estado_ni_origen(self):
        self._post({**self.datos_validos, 'estado': 'asistio', 'origen': 'manual'})
        turno = Turno.objects.get()
        self.assertEqual(turno.estado, 'pendiente')
        self.assertEqual(turno.origen, 'sistema')

    @override_settings(AXES_ENABLED=False)
    def test_carga_manual_del_personal_sin_telefono_ni_direccion(self):
        User.objects.create_user(username='op@test.com', password='Password123!', is_staff=True)
        self.client.login(username='op@test.com', password='Password123!')
        datos = {**self.datos_validos, 'telefono': '', 'direccion': '', 'origen': 'manual'}
        response = self._post(datos)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Turno.objects.get().origen, 'manual')


# ─────────────────────────────────────────────────────────────────────────────
# Tests de correos y reprogramación
# ─────────────────────────────────────────────────────────────────────────────

_EMAIL_OVERRIDE = {
    'AXES_ENABLED': False,
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
}


@override_settings(**_EMAIL_OVERRIDE)
class CorreoCancelacionTests(TestCase):
    """Verifica que se envíe correo al cancelar un turno."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username='admin@test.com', password='Password123!', is_staff=True
        )
        self.turno = Turno.objects.create(
            tramite='dni-nuevo',
            nombre='Ana García',
            dni='12345678',
            email='ana@test.com',
            telefono='3814000000',
            direccion='Av. Belgrano 100',
            fecha=proximo_dia_habil(),
            hora='10:00',
            estado='pendiente',
        )

    def _cambiar_estado(self, estado):
        return self.client.post(
            reverse('api_cambiar_estado', args=[self.turno.id]),
            data=json.dumps({'estado': estado}),
            content_type='application/json',
        )

    def test_cancelar_envia_correo(self):
        """Al cancelar un turno debe enviarse un correo al ciudadano."""
        self.client.force_login(self.staff)
        self._cambiar_estado('cancelado')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('cancelado', mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, ['ana@test.com'])

    def test_correo_cancelacion_contiene_numero_turno(self):
        self.client.force_login(self.staff)
        self._cambiar_estado('cancelado')
        self.assertIn(self.turno.numero_turno, mail.outbox[0].body)

    def test_asistio_no_envia_correo(self):
        """Marcar como 'asistio' NO debe enviar correo."""
        self.client.force_login(self.staff)
        self._cambiar_estado('asistio')
        self.assertEqual(len(mail.outbox), 0)

    def test_no_asistio_no_envia_correo(self):
        self.client.force_login(self.staff)
        self._cambiar_estado('no_asistio')
        self.assertEqual(len(mail.outbox), 0)

    def test_cancelar_requiere_autenticacion(self):
        response = self._cambiar_estado('cancelado')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(**_EMAIL_OVERRIDE)
class ReprogramarTurnoTests(TestCase):
    """Verifica el endpoint POST /api/turnos/<id>/reprogramar/."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username='admin@test.com', password='Password123!', is_staff=True
        )
        self.fecha_original = proximo_dia_habil()
        self.turno = Turno.objects.create(
            tramite='dni-nuevo',
            nombre='Luis Torres',
            dni='87654321',
            email='luis@test.com',
            telefono='3814111111',
            direccion='Av. Libertad 200',
            fecha=self.fecha_original,
            hora='10:00',
            estado='pendiente',
        )
        # Nueva fecha hábil distinta a la original
        d = self.fecha_original + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        self.nueva_fecha = d

    def _reprogramar(self, fecha, hora):
        return self.client.post(
            reverse('api_reprogramar_turno', args=[self.turno.id]),
            data=json.dumps({'fecha': fecha, 'hora': hora}),
            content_type='application/json',
        )

    def test_reprogramar_exitoso_cambia_fecha_y_hora(self):
        self.client.force_login(self.staff)
        response = self._reprogramar(self.nueva_fecha.isoformat(), '09:00')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))
        self.turno.refresh_from_db()
        self.assertEqual(self.turno.fecha, self.nueva_fecha)
        self.assertEqual(self.turno.hora.strftime('%H:%M'), '09:00')

    def test_reprogramar_resetea_estado_a_pendiente(self):
        """Un turno reprogramado debe quedar en estado 'pendiente'."""
        self.turno.estado = 'no_asistio'
        self.turno.save()
        self.client.force_login(self.staff)
        self._reprogramar(self.nueva_fecha.isoformat(), '09:00')
        self.turno.refresh_from_db()
        self.assertEqual(self.turno.estado, 'pendiente')

    def test_reprogramar_envia_correo(self):
        self.client.force_login(self.staff)
        self._reprogramar(self.nueva_fecha.isoformat(), '09:00')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reprogramado', mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, ['luis@test.com'])

    def test_correo_incluye_fecha_anterior_y_nueva(self):
        self.client.force_login(self.staff)
        self._reprogramar(self.nueva_fecha.isoformat(), '09:00')
        cuerpo = mail.outbox[0].body
        self.assertIn(self.fecha_original.strftime('%d/%m/%Y'), cuerpo)
        self.assertIn(self.nueva_fecha.strftime('%d/%m/%Y'), cuerpo)

    def test_error_si_fecha_no_habil(self):
        self.client.force_login(self.staff)
        fin_semana = proximo_fin_de_semana()
        response = self._reprogramar(fin_semana.isoformat(), '09:00')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_error_si_hora_invalida(self):
        self.client.force_login(self.staff)
        response = self._reprogramar(self.nueva_fecha.isoformat(), '14:00')
        self.assertEqual(response.status_code, 400)

    def test_error_si_slot_ocupado(self):
        """No se puede reprogramar a un slot ya ocupado por otro turno."""
        Turno.objects.create(
            tramite='pasaporte',
            nombre='Otro Ciudadano',
            dni='11111111',
            email='otro@test.com',
            telefono='3814999999',
            direccion='Calle Falsa 123',
            fecha=self.nueva_fecha,
            hora='09:00',
            estado='pendiente',
        )
        self.client.force_login(self.staff)
        response = self._reprogramar(self.nueva_fecha.isoformat(), '09:00')
        self.assertEqual(response.status_code, 400)

    def test_reprogramar_requiere_autenticacion(self):
        response = self._reprogramar(self.nueva_fecha.isoformat(), '09:00')
        self.assertEqual(response.status_code, 302)

    def test_error_si_turno_no_existe(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('api_reprogramar_turno', args=[99999]),
            data=json.dumps({'fecha': self.nueva_fecha.isoformat(), 'hora': '09:00'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)


# ─────────────────────────────────────────────────────────────────────────────
# Turnero exclusivo para DNI y sedes
# ─────────────────────────────────────────────────────────────────────────────

from sedes.models import Sede


@override_settings(AXES_ENABLED=False)
class TurnosPorSedeTests(TestCase):

    def setUp(self):
        self.central = Sede.objects.create(nombre='Registro Civil - Sede Central', direccion='Entre Ríos 55',
                                           departamento='Capital', horario='L a V 9 a 13', activo=True,
                                           recibe_turnos_online=True)
        self.banda = Sede.objects.create(nombre='Registro Civil - Sede Banda', direccion='Islas Malvinas 344',
                                         departamento='Banda', horario='L a V 9 a 13', activo=True)
        self.inactiva = Sede.objects.create(nombre='Sede Inactiva', direccion='X 1', departamento='Y',
                                            horario='-', activo=False)
        self.fecha = proximo_dia_habil().isoformat()
        self.datos = {
            'tramite': 'dni-14', 'nombre': 'María González', 'dni': '30123456',
            'email': 'maria@test.com', 'telefono': '3854111111', 'direccion': 'Av. Libertad 200',
            'fecha': self.fecha, 'hora': '09:00',
        }
        User.objects.create_user(username='op@test.com', password='Password123!', is_staff=True)

    def _post(self, data):
        return self.client.post(reverse('api_crear_turno'), data=json.dumps(data), content_type='application/json')

    def test_no_se_puede_sacar_turno_para_pasaporte(self):
        r = self._post({**self.datos, 'tramite': 'pasaporte'})
        self.assertEqual(r.status_code, 400)

    def test_turno_online_va_a_sede_central(self):
        self._post({**self.datos, 'sede_id': self.banda.id})   # el ciudadano no puede elegir sede
        self.assertEqual(Turno.objects.get().sede, self.central)

    def test_carga_manual_en_otra_sede(self):
        self.client.login(username='op@test.com', password='Password123!')
        r = self._post({**self.datos, 'origen': 'manual', 'sede_id': self.banda.id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Turno.objects.get().sede, self.banda)

    def test_carga_manual_sin_sede_usa_central(self):
        self.client.login(username='op@test.com', password='Password123!')
        self._post({**self.datos, 'origen': 'manual'})
        self.assertEqual(Turno.objects.get().sede, self.central)

    def test_carga_manual_en_sede_inactiva_da_error(self):
        self.client.login(username='op@test.com', password='Password123!')
        r = self._post({**self.datos, 'origen': 'manual', 'sede_id': self.inactiva.id})
        self.assertEqual(r.status_code, 400)

    def test_mismo_horario_en_distintas_sedes(self):
        self._post(self.datos)   # 09:00 en la central
        self.client.login(username='op@test.com', password='Password123!')
        r = self._post({**self.datos, 'dni': '99999999', 'origen': 'manual', 'sede_id': self.banda.id})
        self.assertEqual(r.status_code, 200)

    def test_disponibilidad_por_sede(self):
        self._post(self.datos)
        url = reverse('api_disponibilidad')
        central = self.client.get(url, {'fecha': self.fecha}).json()
        banda = self.client.get(url, {'fecha': self.fecha, 'sede': self.banda.id}).json()
        self.assertTrue(next(s for s in central['slots'] if s['hora'] == '09:00')['lleno'])
        self.assertFalse(next(s for s in banda['slots'] if s['hora'] == '09:00')['lleno'])

    def test_turnos_sin_sede_cuentan_para_la_central(self):
        Turno.objects.create(tramite='dni-14', nombre='Viejo Turno', dni='11111111', email='v@test.com',
                             telefono='3854000000', direccion='Calle 1', fecha=self.fecha, hora='09:00')
        r = self._post({**self.datos, 'dni': '22222222'})
        self.assertEqual(r.status_code, 400)
