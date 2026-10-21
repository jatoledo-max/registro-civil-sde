import re
from decimal import Decimal, InvalidOperation
import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from auditoria.registro import diferencias, foto, registrar
from .models import Tramite, CategoriaTramite

CAMPOS_AUDITADOS = ['nombre', 'descripcion', 'slug', 'categoria', 'precio', 'es_gratuito', 'requiere_turno',
                    'requisitos', 'como_se_inicia', 'modalidad_presencial', 'modalidad_digital', 'icono', 'estado']

import logging
from usuarios.views import es_superadmin
logger = logging.getLogger(__name__)


def lista_tramites(request):
    categorias = CategoriaTramite.objects.prefetch_related('tramites').all()
    resultado  = []

    for cat in categorias:
        tramites_pub = cat.tramites.filter(estado='publicado')
        if tramites_pub.exists():
            resultado.append({
                'id':       cat.id,
                'nombre':   cat.nombre,
                'icono':    cat.icono,
                'tramites': list(tramites_pub.values('id', 'nombre', 'descripcion', 'slug', 'icono'))
            })

    return render(request, 'tramites.html', {'categorias': resultado})

# ── API para el panel admin ──


RE_SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def validar_tramite(nombre, precio, slug=None):
    """Devuelve un mensaje de error o None."""
    if not nombre:
        return 'El nombre es obligatorio.'
    if len(nombre) > 200:
        return 'El nombre no puede superar los 200 caracteres.'
    if slug is not None and (len(slug) > 100 or not RE_SLUG.match(slug)):
        return 'El identificador de URL solo puede tener minúsculas, números y guiones (ej: partida-nacimiento).'
    if precio not in (None, ''):
        try:
            if Decimal(str(precio)) < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return 'El precio debe ser un número mayor o igual a 0.'
    return None

@login_required
def api_listar_tramites(request):
    tramites = Tramite.objects.select_related('categoria', 'creado_por', 'aprobado_por').all()
    data = []
    for t in tramites:
        data.append({
            'id':         t.id,
            'nombre':     t.nombre,
            'categoria':  t.categoria.nombre if t.categoria else '—',
            'slug':       t.slug,
            'icono':      t.icono,
            'estado':     t.estado,
            'creado_por': (
                'Admin'    if t.creado_por and es_superadmin(t.creado_por) else
                'Operador' if t.creado_por and t.creado_por.is_staff else
                'Sistema'
            ),
            'es_gratuito':          t.es_gratuito,
            'precio':               str(t.precio) if t.precio else None,
            'requiere_turno':       t.requiere_turno,
            'requisitos':           t.requisitos,
            'como_se_inicia':       t.como_se_inicia,
            'modalidad_presencial': t.modalidad_presencial,
            'modalidad_digital':    t.modalidad_digital,
        })
    return JsonResponse({'tramites': data})


@login_required
@require_POST
def api_crear_tramite(request):
    try:
        data        = json.loads(request.body)
        nombre      = data.get('nombre', '').strip()
        descripcion = data.get('descripcion', '').strip()
        slug        = data.get('slug', '').strip()
        icono       = data.get('icono', 'bi-file-earmark-text').strip()
        categoria_id = data.get('categoria_id')
        es_gratuito          = data.get('es_gratuito', False)
        requiere_turno       = data.get('requiere_turno', False)
        requisitos           = data.get('requisitos', '').strip()
        como_se_inicia       = data.get('como_se_inicia', '').strip()
        modalidad_presencial = data.get('modalidad_presencial', False)
        modalidad_digital    = data.get('modalidad_digital', False)
        precio               = data.get('precio') or None

        if not nombre or not slug:
            return JsonResponse({'error': 'Nombre y slug son obligatorios.'}, status=400)

        error = validar_tramite(nombre, precio, slug)
        if error:
            return JsonResponse({'error': error}, status=400)

        if Tramite.objects.filter(slug=slug).exists():
            return JsonResponse({'error': 'Ya existe un trámite con ese slug.'}, status=400)

        estado = 'borrador'
        fecha_pub = None
        if es_superadmin(request.user) and data.get('estado') == 'publicado':
            estado    = 'publicado'
            fecha_pub = timezone.now()

        tramite = Tramite.objects.create(
            nombre       = nombre,
            descripcion  = descripcion,
            slug         = slug,
            icono        = icono,
            estado       = estado,
            categoria_id = categoria_id,
            creado_por   = request.user,
            fecha_publicacion = fecha_pub,
            es_gratuito          = es_gratuito,
            requiere_turno       = requiere_turno,
            requisitos           = requisitos,
            como_se_inicia       = como_se_inicia,
            modalidad_presencial = modalidad_presencial,
            modalidad_digital    = modalidad_digital,
            precio               = precio,
        )
        registrar(request, 'crear', 'tramites', tramite.id, tramite.nombre, foto(tramite, CAMPOS_AUDITADOS))
        return JsonResponse({'ok': True, 'id': tramite.id})

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)
    
@login_required
@require_POST
def api_crear_categoria(request):
    try:
        data   = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        icono  = data.get('icono', 'bi-file-earmark').strip()

        if not nombre:
            return JsonResponse({'error': 'El nombre es obligatorio.'}, status=400)

        if CategoriaTramite.objects.filter(nombre__iexact=nombre).exists():
            return JsonResponse({'error': 'Ya existe una categoría con ese nombre.'}, status=400)

        orden = CategoriaTramite.objects.count() + 1
        cat   = CategoriaTramite.objects.create(nombre=nombre, icono=icono, orden=orden)
        registrar(request, 'crear', 'categorias', cat.id, cat.nombre, foto(cat, ['nombre', 'icono', 'orden']))
        return JsonResponse({'ok': True, 'id': cat.id, 'nombre': cat.nombre, 'icono': cat.icono})

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
@require_POST
def api_editar_tramite(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    try:
        data    = json.loads(request.body)
        antes   = foto(tramite, CAMPOS_AUDITADOS)

        tramite.nombre      = data.get('nombre', tramite.nombre).strip()
        tramite.descripcion = data.get('descripcion', tramite.descripcion).strip()
        tramite.icono       = data.get('icono', tramite.icono).strip()
        tramite.es_gratuito          = data.get('es_gratuito', tramite.es_gratuito)
        tramite.requiere_turno       = data.get('requiere_turno', tramite.requiere_turno)
        tramite.requisitos           = data.get('requisitos', tramite.requisitos).strip()
        tramite.como_se_inicia       = data.get('como_se_inicia', tramite.como_se_inicia).strip()
        tramite.modalidad_presencial = data.get('modalidad_presencial', tramite.modalidad_presencial)
        tramite.modalidad_digital    = data.get('modalidad_digital', tramite.modalidad_digital)
        tramite.precio               = data.get('precio') or None

        error = validar_tramite(tramite.nombre, tramite.precio)
        if error:
            return JsonResponse({'error': error}, status=400)

        if data.get('categoria_id'):
            tramite.categoria_id = data['categoria_id']

        # Solo superadmin puede aprobar
        nuevo_estado = data.get('estado')
        if nuevo_estado and nuevo_estado not in dict(Tramite.ESTADOS):
            return JsonResponse({'error': 'Estado inválido.'}, status=400)
        if nuevo_estado and es_superadmin(request.user):
            tramite.estado = nuevo_estado
            if nuevo_estado == 'publicado' and not tramite.fecha_publicacion:
                tramite.fecha_publicacion = timezone.now()
                tramite.aprobado_por      = request.user
        elif nuevo_estado and nuevo_estado != 'publicado':
            tramite.estado = nuevo_estado

        tramite.save()
        cambios = diferencias(antes, foto(tramite, CAMPOS_AUDITADOS))
        if cambios:
            registrar(request, 'editar', 'tramites', tramite.id, tramite.nombre, cambios)
        return JsonResponse({'ok': True})

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
@require_POST
def api_eliminar_tramite(request, tramite_id):
    try:
        if not es_superadmin(request.user):
            return JsonResponse({'error': 'No tenés permisos para eliminar trámites.'}, status=403)

        tramite = Tramite.objects.filter(id=tramite_id).first()
        if not tramite:
            return JsonResponse({'error': 'Trámite no encontrado.'}, status=404)
        copia = foto(tramite, CAMPOS_AUDITADOS)
        tramite.delete()
        registrar(request, 'eliminar', 'tramites', tramite_id, copia['nombre'], copia)
        return JsonResponse({'ok': True})

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
def api_listar_categorias(request):
    categorias = CategoriaTramite.objects.all()
    data = [{'id': c.id, 'nombre': c.nombre, 'icono': c.icono} for c in categorias]
    return JsonResponse({'categorias': data})