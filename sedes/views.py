import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from usuarios.views import es_superadmin
from auditoria.registro import diferencias, foto, registrar
from .models import Sede

CAMPOS_AUDITADOS = ['nombre', 'direccion', 'referencia', 'departamento', 'provincia', 'horario',
                    'latitud', 'longitud', 'activo', 'recibe_turnos_online']

import logging
logger = logging.getLogger(__name__)

# Límites aproximados de la provincia de Santiago del Estero (con margen)
LIMITES_SDE = {'lat': (-30.5, -25.0), 'lng': (-65.8, -61.0)}


def validar_sede(nombre, direccion, departamento, horario, referencia, lat, lng):
    """Devuelve un mensaje de error o None.
    La ubicación se marca en el mapa del panel, así que las coordenadas son obligatorias."""
    if not nombre or not direccion or not departamento or not horario:
        return 'Completá los campos obligatorios.'
    if (len(nombre) > 100 or len(direccion) > 200 or len(departamento) > 100
            or len(horario) > 200 or len(referencia) > 200):
        return 'Alguno de los campos supera el largo permitido.'
    if lat in (None, '') or lng in (None, ''):
        return 'Marcá la ubicación de la sede en el mapa.'
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError):
        return 'La ubicación marcada no es válida.'
    if not (LIMITES_SDE['lat'][0] <= lat_f <= LIMITES_SDE['lat'][1]
            and LIMITES_SDE['lng'][0] <= lng_f <= LIMITES_SDE['lng'][1]):
        return 'La ubicación marcada está fuera de Santiago del Estero.'
    return None


def texto(data, campo, defecto=''):
    return str(data.get(campo, defecto) or '').strip()


def sede_a_dict(s):
    return {
        'id':           s.id,
        'nombre':       s.nombre,
        'direccion':    s.direccion,
        'departamento': s.departamento,
        'provincia':    s.provincia,
        'horario':      s.horario,
        'referencia':   s.referencia,
        'lat':          float(s.latitud)  if s.latitud  is not None else None,
        'lng':          float(s.longitud) if s.longitud is not None else None,
        'activo':       s.activo,
        'recibe_turnos_online': s.recibe_turnos_online,
    }


def aplicar_turnos_online(request, sede, valor):
    """Por ahora solo una sede recibe los turnos online: al marcar una se desmarcan las demás."""
    sede.recibe_turnos_online = bool(valor)
    if sede.recibe_turnos_online:
        for otra in Sede.objects.exclude(pk=sede.pk).filter(recibe_turnos_online=True):
            registrar(request, 'editar', 'sedes', otra.id, otra.nombre,
                      {'recibe_turnos_online': [True, False]})
        Sede.objects.exclude(pk=sede.pk).update(recibe_turnos_online=False)


@login_required
def listar_sedes(request):
    return JsonResponse({'sedes': [sede_a_dict(s) for s in Sede.objects.all()]})


@login_required
@require_POST
def crear_sede(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    try:
        nombre       = texto(data, 'nombre')
        direccion    = texto(data, 'direccion')
        departamento = texto(data, 'departamento')
        provincia    = texto(data, 'provincia') or 'Santiago del Estero'
        horario      = texto(data, 'horario')
        referencia   = texto(data, 'referencia')
        lat, lng     = data.get('lat'), data.get('lng')

        error = validar_sede(nombre, direccion, departamento, horario, referencia, lat, lng)
        if error:
            return JsonResponse({'error': error}, status=400)

        # Solo un Super Admin puede aprobar la sede o asignarle los turnos online
        superadmin = es_superadmin(request.user)

        sede = Sede(
            nombre       = nombre,
            direccion    = direccion,
            departamento = departamento,
            provincia    = provincia,
            horario      = horario,
            referencia   = referencia,
            latitud      = round(float(lat), 6),
            longitud     = round(float(lng), 6),
            activo       = bool(data.get('activo')) if superadmin else False,
            creado_por   = request.user,
        )
        sede.save()
        if superadmin and data.get('recibe_turnos_online'):
            aplicar_turnos_online(request, sede, True)
            sede.save()

        registrar(request, 'crear', 'sedes', sede.id, sede.nombre, foto(sede, CAMPOS_AUDITADOS))
        return JsonResponse({'ok': True, 'id': sede.id})

    except Exception:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
@require_POST
def editar_sede(request, sede_id):
    sede = get_object_or_404(Sede, id=sede_id)
    antes = foto(sede, CAMPOS_AUDITADOS)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    try:
        nombre       = texto(data, 'nombre', sede.nombre)
        direccion    = texto(data, 'direccion', sede.direccion)
        departamento = texto(data, 'departamento', sede.departamento)
        provincia    = texto(data, 'provincia', sede.provincia) or 'Santiago del Estero'
        horario      = texto(data, 'horario', sede.horario)
        referencia   = texto(data, 'referencia', sede.referencia)
        lat          = data.get('lat', sede.latitud)
        lng          = data.get('lng', sede.longitud)

        error = validar_sede(nombre, direccion, departamento, horario, referencia, lat, lng)
        if error:
            return JsonResponse({'error': error}, status=400)

        sede.nombre       = nombre
        sede.direccion    = direccion
        sede.departamento = departamento
        sede.provincia    = provincia
        sede.horario      = horario
        sede.referencia   = referencia
        sede.latitud      = round(float(lat), 6)
        sede.longitud     = round(float(lng), 6)

        # Solo un Super Admin puede cambiar el estado o la sede de turnos online
        activo, turnos_online = sede.activo, sede.recibe_turnos_online
        if es_superadmin(request.user):
            activo = bool(data.get('activo', sede.activo))
            turnos_online = bool(data.get('recibe_turnos_online', sede.recibe_turnos_online))

        if sede.recibe_turnos_online and not turnos_online:
            return JsonResponse(
                {'error': 'Siempre tiene que haber una sede que reciba los turnos online: '
                          'para cambiarla, marcá la opción en la otra sede.'}, status=400
            )
        if turnos_online and not activo:
            return JsonResponse(
                {'error': 'La sede que recibe los turnos online tiene que estar activa.'}, status=400
            )

        sede.activo = activo
        aplicar_turnos_online(request, sede, turnos_online)
        sede.save()
        sede.refresh_from_db()
        cambios = diferencias(antes, foto(sede, CAMPOS_AUDITADOS))
        if cambios:
            registrar(request, 'editar', 'sedes', sede.id, sede.nombre, cambios)
        return JsonResponse({'ok': True})

    except Exception:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
@require_POST
def eliminar_sede(request, sede_id):
    sede = get_object_or_404(Sede, id=sede_id)
    try:

        # Solo superadmin puede eliminar
        if not es_superadmin(request.user):
            return JsonResponse({'error': 'No tenés permisos para eliminar sedes.'}, status=403)

        if sede.recibe_turnos_online:
            return JsonResponse(
                {'error': 'No se puede eliminar la sede que recibe los turnos online. '
                          'Asigná los turnos a otra sede primero.'}, status=400
            )

        copia = foto(sede, CAMPOS_AUDITADOS)
        sede.delete()
        registrar(request, 'eliminar', 'sedes', sede_id, copia['nombre'], copia)
        return JsonResponse({'ok': True})

    except Exception:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)
