from django.test import TestCase

# Create your tests here.


from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse


@override_settings(AXES_ENABLED=False)
class ValidacionNoticiasTests(TestCase):

    def setUp(self):
        User.objects.create_superuser(username='sa@test.com', password='Password123!')
        self.client.login(username='sa@test.com', password='Password123!')
        self.url = reverse('api_crear_noticia')

    def test_crea_noticia_valida(self):
        r = self.client.post(self.url, {'titulo': 'Nueva sede', 'cuerpo': 'Texto', 'tag': 'General'})
        self.assertEqual(r.status_code, 200)

    def test_titulo_muy_largo(self):
        r = self.client.post(self.url, {'titulo': 'x' * 201, 'cuerpo': 'Texto', 'tag': 'General'})
        self.assertEqual(r.status_code, 400)

    def test_tag_invalido(self):
        r = self.client.post(self.url, {'titulo': 'Hola', 'cuerpo': 'Texto', 'tag': 'Spam'})
        self.assertEqual(r.status_code, 400)

    def test_archivo_que_no_es_imagen(self):
        falso = SimpleUploadedFile('foto.png', b'esto no es una imagen', content_type='image/png')
        r = self.client.post(self.url, {'titulo': 'Hola', 'cuerpo': 'Texto', 'tag': 'General', 'imagen': falso})
        self.assertEqual(r.status_code, 400)
