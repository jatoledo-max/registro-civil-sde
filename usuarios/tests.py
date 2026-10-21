"""
Tests para la app 'usuarios'.
Cubre: listar, crear, editar y desactivar usuarios del panel admin.

Ejecutar con:
    python manage.py test usuarios
"""

import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from .models import PerfilEmpleado


@override_settings(AXES_ENABLED=False)
class ListarUsuariosTests(TestCase):
    """Pruebas del endpoint GET /api/usuarios/."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin@test.com',
            password='Password123!',
            is_staff=True,
        )
        PerfilEmpleado.objects.create(user=self.admin, rol='super_admin')

    def test_requiere_autenticacion(self):
        response = self.client.get(reverse('listar_usuarios'))
        self.assertEqual(response.status_code, 302)

    def test_retorna_lista_de_usuarios(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('listar_usuarios'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('usuarios', data)
        self.assertIsInstance(data['usuarios'], list)

    def test_respuesta_incluye_campos_esperados(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('listar_usuarios'))
        data = response.json()
        if data['usuarios']:
            usuario = data['usuarios'][0]
            for campo in ['id', 'nombre', 'email', 'rol', 'activo', 'fecha_alta']:
                self.assertIn(campo, usuario)


@override_settings(AXES_ENABLED=False)
class CrearUsuarioTests(TestCase):
    """Pruebas del endpoint POST /api/usuarios/crear/."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin@test.com',
            password='Password123!',
            is_staff=True,
        )
        PerfilEmpleado.objects.create(user=self.admin, rol='super_admin')

    def _post(self, data):
        return self.client.post(
            reverse('crear_usuario'),
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_requiere_autenticacion(self):
        response = self._post({'nombre': 'Test', 'email': 'x@x.com', 'password': '123'})
        self.assertEqual(response.status_code, 302)

    def test_crea_usuario_con_datos_validos(self):
        self.client.force_login(self.admin)
        response = self._post({
            'nombre':   'María González',
            'email':    'maria@test.com',
            'password': 'Password123!',
            'rol':      'operador',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertTrue(User.objects.filter(username='maria@test.com').exists())

    def test_crea_perfil_de_empleado(self):
        self.client.force_login(self.admin)
        self._post({
            'nombre':   'Carlos López',
            'email':    'carlos@test.com',
            'password': 'Password123!',
            'rol':      'operador',
        })
        user = User.objects.get(username='carlos@test.com')
        self.assertTrue(hasattr(user, 'perfil'))
        self.assertEqual(user.perfil.rol, 'operador')

    def test_separa_nombre_y_apellido(self):
        self.client.force_login(self.admin)
        self._post({
            'nombre':   'Ana Martínez',
            'email':    'ana@test.com',
            'password': 'Password123!',
        })
        user = User.objects.get(username='ana@test.com')
        self.assertEqual(user.first_name, 'Ana')
        self.assertEqual(user.last_name, 'Martínez')

    def test_error_si_faltan_campos(self):
        self.client.force_login(self.admin)
        response = self._post({'nombre': 'Solo Nombre'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_error_si_email_duplicado(self):
        self.client.force_login(self.admin)
        self._post({
            'nombre':   'Primer Usuario',
            'email':    'duplicado@test.com',
            'password': 'Password123!',
        })
        response = self._post({
            'nombre':   'Segundo Usuario',
            'email':    'duplicado@test.com',
            'password': 'Password123!',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_nuevo_usuario_tiene_is_staff(self):
        """Los empleados creados deben poder acceder al panel (is_staff=True)."""
        self.client.force_login(self.admin)
        self._post({
            'nombre':   'Nuevo Empleado',
            'email':    'empleado@test.com',
            'password': 'Password123!',
        })
        user = User.objects.get(username='empleado@test.com')
        self.assertTrue(user.is_staff)


@override_settings(AXES_ENABLED=False)
class EditarUsuarioTests(TestCase):
    """Pruebas del endpoint POST /api/usuarios/<id>/editar/."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin@test.com',
            password='Password123!',
            is_staff=True,
        )
        PerfilEmpleado.objects.create(user=self.admin, rol='super_admin')

        self.empleado = User.objects.create_user(
            username='empleado@test.com',
            email='empleado@test.com',
            first_name='Pedro',
            last_name='Sánchez',
            password='Password123!',
            is_staff=True,
        )
        PerfilEmpleado.objects.create(user=self.empleado, rol='operador')

    def _post(self, user_id, data):
        return self.client.post(
            reverse('editar_usuario', args=[user_id]),
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_requiere_autenticacion(self):
        response = self._post(self.empleado.id, {'nombre': 'Nuevo'})
        self.assertEqual(response.status_code, 302)

    def test_edita_nombre(self):
        self.client.force_login(self.admin)
        self._post(self.empleado.id, {'nombre': 'Pedro Actualizado'})
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.first_name, 'Pedro')

    def test_edita_rol(self):
        self.client.force_login(self.admin)
        self._post(self.empleado.id, {'rol': 'super_admin'})
        self.empleado.perfil.refresh_from_db()
        self.assertEqual(self.empleado.perfil.rol, 'super_admin')

    def test_retorna_ok_en_exito(self):
        self.client.force_login(self.admin)
        response = self._post(self.empleado.id, {'nombre': 'Nuevo Nombre'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))

    def test_error_si_usuario_no_existe(self):
        self.client.force_login(self.admin)
        response = self._post(99999, {'nombre': 'No Existe'})
        self.assertEqual(response.status_code, 404)


@override_settings(AXES_ENABLED=False)
class DesactivarUsuarioTests(TestCase):
    """Pruebas del endpoint POST /api/usuarios/<id>/desactivar/."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin@test.com',
            password='Password123!',
            is_staff=True,
        )
        PerfilEmpleado.objects.create(user=self.admin, rol='super_admin')

        self.empleado = User.objects.create_user(
            username='empleado@test.com',
            password='Password123!',
            is_staff=True,
            is_active=True,
        )
        PerfilEmpleado.objects.create(user=self.empleado, rol='operador')

    def _post(self, user_id):
        return self.client.post(
            reverse('desactivar_usuario', args=[user_id]),
            content_type='application/json',
        )

    def test_requiere_autenticacion(self):
        response = self._post(self.empleado.id)
        self.assertEqual(response.status_code, 302)

    def test_desactiva_usuario_activo(self):
        self.client.force_login(self.admin)
        self._post(self.empleado.id)
        self.empleado.refresh_from_db()
        self.assertFalse(self.empleado.is_active)

    def test_reactiva_usuario_inactivo(self):
        self.empleado.is_active = False
        self.empleado.save()
        self.client.force_login(self.admin)
        self._post(self.empleado.id)
        self.empleado.refresh_from_db()
        self.assertTrue(self.empleado.is_active)

    def test_no_puede_desactivarse_a_si_mismo(self):
        """Un usuario no puede desactivar su propia cuenta."""
        self.client.force_login(self.admin)
        response = self._post(self.admin.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


@override_settings(AXES_ENABLED=False)
class PermisosYValidacionUsuariosTests(TestCase):
    """Solo un Super Admin gestiona usuarios; los datos se validan en el servidor."""

    def setUp(self):
        self.admin = User.objects.create_user(username='sa@test.com', password='Password123!', is_staff=True)
        PerfilEmpleado.objects.create(user=self.admin, rol='super_admin')
        self.operador = User.objects.create_user(username='op@test.com', password='Password123!', is_staff=True)
        PerfilEmpleado.objects.create(user=self.operador, rol='operador')
        self.url = reverse('crear_usuario')

    def _post(self, data):
        return self.client.post(self.url, data=json.dumps(data), content_type='application/json')

    def test_operador_no_puede_crear_usuarios(self):
        self.client.login(username='op@test.com', password='Password123!')
        r = self._post({'nombre': 'Ana Gómez', 'email': 'ana@test.com', 'password': 'Password123!', 'rol': 'super_admin'})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(User.objects.filter(username='ana@test.com').exists())

    def test_email_invalido(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post({'nombre': 'Ana Gómez', 'email': 'ana@', 'password': 'Password123!'})
        self.assertEqual(r.status_code, 400)

    def test_password_debil(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post({'nombre': 'Ana Gómez', 'email': 'ana@test.com', 'password': '1234'})
        self.assertEqual(r.status_code, 400)

    def test_rol_invalido(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self._post({'nombre': 'Ana Gómez', 'email': 'ana@test.com', 'password': 'Password123!', 'rol': 'dios'})
        self.assertEqual(r.status_code, 400)

    def test_editar_con_email_de_otro_usuario(self):
        self.client.login(username='sa@test.com', password='Password123!')
        r = self.client.post(reverse('editar_usuario', args=[self.operador.id]),
                             data=json.dumps({'email': 'sa@test.com'}), content_type='application/json')
        self.assertEqual(r.status_code, 400)
