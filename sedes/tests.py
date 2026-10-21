from django.test import TestCase

# Create your tests here.


import json
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse


@override_settings(AXES_ENABLED=False)
class ValidacionSedesTests(TestCase):

    def setUp(self):
        User.objects.create_superuser(username='sa@test.com', password='Password123!')
        self.client.login(username='sa@test.com', password='Password123!')

    def _crear(self, **extra):
        data = {'nombre': 'Sede Test', 'direccion': 'Belgrano 100', 'departamento': 'Capital',
                'horario': 'Lunes a Viernes 09:00 a 13:00', 'lat': '-27.79', 'lng': '-64.26', **extra}
        return self.client.post(reverse('crear_sede'), data=json.dumps(data), content_type='application/json')

    def test_crea_con_coordenadas_validas(self):
        self.assertEqual(self._crear().status_code, 200)

    def test_coordenadas_fuera_de_rango(self):
        self.assertEqual(self._crear(lat='-127.5').status_code, 400)

    def test_solo_una_coordenada(self):
        self.assertEqual(self._crear(lng='').status_code, 400)

    def test_faltan_campos(self):
        self.assertEqual(self._crear(horario='').status_code, 400)


from .models import Sede


@override_settings(AXES_ENABLED=False)
class GestionSedesMapaTests(TestCase):
    """La ubicación se marca en el mapa y el Super Admin elige la sede de turnos online."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username='sa@test.com', password='Password123!')
        self.operador = User.objects.create_user(username='op@test.com', password='Password123!', is_staff=True)
        self.central = Sede.objects.create(nombre='Sede Central', direccion='Andes y Belgrano Norte',
                                           departamento='Capital', horario='L a V', latitud='-27.783840',
                                           longitud='-64.266950', activo=True, recibe_turnos_online=True)
        self.banda = Sede.objects.create(nombre='Sede Banda', direccion='Islas Malvinas 344',
                                         departamento='Banda', horario='L a V', latitud='-27.735',
                                         longitud='-64.243', activo=True)

    def _post(self, url, data):
        return self.client.post(url, data=json.dumps(data), content_type='application/json')

    def _datos(self, **extra):
        return {'nombre': 'Sede Nueva', 'direccion': 'Belgrano 100', 'departamento': 'Capital',
                'horario': 'L a V', 'referencia': 'Frente a la plaza', 'lat': '-27.79', 'lng': '-64.26', **extra}

    def test_crear_sin_ubicacion_da_error(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post(reverse('crear_sede'), self._datos(lat='', lng=''))
        self.assertEqual(r.status_code, 400)
        self.assertIn('mapa', r.json()['error'])

    def test_ubicacion_fuera_de_santiago_del_estero(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post(reverse('crear_sede'), self._datos(lat='-34.60', lng='-58.38'))   # CABA
        self.assertEqual(r.status_code, 400)

    def test_guarda_referencia(self):
        self.client.login(username='sa@test.com', password='Password123!')
        self._post(reverse('crear_sede'), self._datos())
        self.assertEqual(Sede.objects.get(nombre='Sede Nueva').referencia, 'Frente a la plaza')

    def test_operador_no_activa_ni_asigna_turnos_online(self):
        self.client.login(username='op@test.com', password='Password123!')
        self._post(reverse('crear_sede'), self._datos(activo=True, recibe_turnos_online=True))
        sede = Sede.objects.get(nombre='Sede Nueva')
        self.assertFalse(sede.activo)
        self.assertFalse(sede.recibe_turnos_online)
        self.central.refresh_from_db()
        self.assertTrue(self.central.recibe_turnos_online)

    def test_marcar_otra_sede_desmarca_la_anterior(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post(reverse('editar_sede', args=[self.banda.id]), {'recibe_turnos_online': True, 'activo': True})
        self.assertEqual(r.status_code, 200)
        self.central.refresh_from_db(); self.banda.refresh_from_db()
        self.assertFalse(self.central.recibe_turnos_online)
        self.assertTrue(self.banda.recibe_turnos_online)

    def test_no_se_puede_dejar_sin_sede_de_turnos_online(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post(reverse('editar_sede', args=[self.central.id]), {'recibe_turnos_online': False})
        self.assertEqual(r.status_code, 400)

    def test_sede_de_turnos_online_debe_estar_activa(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post(reverse('editar_sede', args=[self.central.id]), {'activo': False})
        self.assertEqual(r.status_code, 400)

    def test_no_se_puede_eliminar_la_sede_de_turnos_online(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self.client.post(reverse('eliminar_sede', args=[self.central.id]))
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Sede.objects.filter(pk=self.central.pk).exists())

    def test_editar_mueve_el_punto_en_el_mapa(self):
        self.client.login(username='sa@test.com', password='Password123!')
        self._post(reverse('editar_sede', args=[self.banda.id]), {'lat': '-27.7301', 'lng': '-64.2402'})
        self.banda.refresh_from_db()
        self.assertAlmostEqual(float(self.banda.latitud), -27.7301, places=4)

    @override_settings(STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_pagina_publica_muestra_referencia_y_turnos_online(self):
        self.central.referencia = 'Frente a la plaza'
        self.central.save()
        html = self.client.get(reverse('sedes')).content.decode()
        self.assertIn('Frente a la plaza', html)
        self.assertIn('"turnos_online": true', html)
