from django.test import TestCase

# Create your tests here.


import json
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse


@override_settings(AXES_ENABLED=False)
class ValidacionTramitesTests(TestCase):

    def setUp(self):
        User.objects.create_superuser(username='sa@test.com', password='Password123!')
        self.client.login(username='sa@test.com', password='Password123!')

    def _crear(self, **extra):
        data = {'nombre': 'Partida de nacimiento', 'slug': 'partida-nacimiento', **extra}
        return self.client.post(reverse('api_crear_tramite'), data=json.dumps(data), content_type='application/json')

    def test_crea_con_datos_validos(self):
        self.assertEqual(self._crear().status_code, 200)

    def test_slug_invalido(self):
        for slug in ['Partida Nacimiento', 'partida_nacimiento', '../admin', '-x-']:
            self.assertEqual(self._crear(slug=slug).status_code, 400, slug)

    def test_precio_negativo_o_no_numerico(self):
        self.assertEqual(self._crear(precio=-10).status_code, 400)
        self.assertEqual(self._crear(precio='abc').status_code, 400)
