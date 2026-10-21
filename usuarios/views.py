import json
import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from auditoria.registro import registrar
from .models import PerfilEmpleado

import logging
logger = logging.getLogger(__name__)

ROLES_VALIDOS = {clave for clave, _ in PerfilEmpleado.ROLES}
RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]{3,100}$")


def es_superadmin(user):
    """Superusuario de Django o empleado con rol 'super_admin'."""
    if user.is_superuser:
        return True
    perfil = getattr(user, 'perfil', None)
    return bool(perfil and perfil.rol == 'super_admin')


def sin_permiso():
    return JsonResponse({'error': 'Solo un Super Admin puede gestionar usuarios.'}, status=403)


def validar_usuario(nombre, email, password, rol, user=None):
    """Devuelve un mensaje de error o None."""
    if nombre and not RE_NOMBRE.match(nombre):
        return 'El nombre solo puede contener letras (entre 3 y 100 caracteres).'
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return 'Ingresá un correo electrónico válido.'
        if User.objects.filter(username__iexact=email).exclude(pk=getattr(user, 'pk', None)).exists():
            return 'Ya existe un usuario con ese correo.'
    if rol and rol not in ROLES_VALIDOS:
        return 'Rol inválido.'
    if password:
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            return ' '.join(e.messages)
    return None


@login_required
def listar_usuarios(request):
    empleados = PerfilEmpleado.objects.select_related('user').all()
    data = []
    for emp in empleados:
        data.append({
            'id': emp.user.id,
            'nombre': emp.user.get_full_name(),
            'email': emp.user.email,
            'rol': emp.rol,
            'activo': emp.user.is_active,
            'fecha_alta': emp.fecha_alta.strftime('%d/%m/%Y'),
        })
    return JsonResponse({'usuarios': data})


@login_required
@require_POST
def crear_usuario(request):
    if not es_superadmin(request.user):
        return sin_permiso()
    try:
        data = json.loads(request.body)
        nombre = ' '.join(str(data.get('nombre') or '').split())
        email = str(data.get('email') or '').strip().lower()
        password = str(data.get('password') or '').strip()
        rol = data.get('rol') or 'operador'

        if not nombre or not email or not password:
            return JsonResponse({'error':'Todos los campos son obligatorios.'}, status=400)

        error = validar_usuario(nombre, email, password, rol)
        if error:
            return JsonResponse({'error': error}, status=400)

        # Separamos nombre y apellido
        partes = nombre.split(' ',1)
        first = partes[0]
        last = partes[1] if len(partes) > 1 else ''

        user = User.objects.create_user(
            username = email,
            email = email,
            password = password,
            first_name = first,
            last_name = last,
            is_staff = True,
        )
        # La contraseña inicial la conoce quien creó la cuenta: se pide cambiarla al primer ingreso
        PerfilEmpleado.objects.create(user=user, rol=rol, debe_cambiar_password=True)

        registrar(request, 'crear', 'usuarios', user.id, nombre,
                  {'nombre': nombre, 'email': email, 'rol': rol, 'contraseña': 'temporal asignada'})
        return JsonResponse({'ok':True,'id':user.id})

    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)


@login_required
@require_POST
def editar_usuario(request, user_id):
    if not es_superadmin(request.user):
        return sin_permiso()
    user = get_object_or_404(User, id=user_id)
    perfil = get_object_or_404(PerfilEmpleado, user=user)
    try:
        data = json.loads(request.body)

        nombre = ' '.join(str(data.get('nombre') or '').split())
        email = str(data.get('email') or '').strip().lower()
        password = str(data.get('password') or '').strip()
        rol = data.get('rol')

        error = validar_usuario(nombre, email, password, rol, user=user)
        if error:
            return JsonResponse({'error': error}, status=400)

        if user == request.user and rol and rol != perfil.rol:
            return JsonResponse({'error': 'No podés cambiar tu propio rol.'}, status=400)

        antes = {'nombre': user.get_full_name(), 'email': user.email, 'rol': perfil.rol}

        if nombre:
            partes = nombre.split(' ',1)
            user.first_name = partes[0]
            user.last_name  = partes[1] if len(partes) > 1 else ''

        if email:
            user.email = email
            user.username = email

        if password:
            user.set_password(password)
            # Si la blanquea otra persona, el dueño de la cuenta debe elegir una nueva al ingresar
            perfil.debe_cambiar_password = (user != request.user)

        if rol:
            perfil.rol = rol

        user.save()
        perfil.save()

        despues = {'nombre': user.get_full_name(), 'email': user.email, 'rol': perfil.rol}
        cambios = {c: [antes[c], despues[c]] for c in despues if antes[c] != despues[c]}
        if password:
            # Nunca se guarda la contraseña: solo que fue blanqueada
            cambios['contraseña'] = ['(oculta)', 'blanqueada (temporal)' if user != request.user else 'cambiada']
        if cambios:
            registrar(request, 'editar', 'usuarios', user.id, user.get_full_name() or user.username, cambios)
        return JsonResponse({'ok':True})

    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)


@login_required
@require_POST
def desactivar_usuario(request, user_id):
    if not es_superadmin(request.user):
        return sin_permiso()
    user = get_object_or_404(User, id=user_id)
    try:

        # No permitir que se desactive a sí mismo
        if user == request.user:
            return JsonResponse({'error':'No podés desactivar tu propio usuario.'},status=400)

        user.is_active = not user.is_active
        user.save()
        registrar(request, 'activar' if user.is_active else 'desactivar', 'usuarios',
                  user.id, user.get_full_name() or user.username, {'activo': [not user.is_active, user.is_active]})

        estado ='activado' if user.is_active else 'desactivado'
        return JsonResponse({'ok': True, 'estado':estado, 'activo':user.is_active})

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)