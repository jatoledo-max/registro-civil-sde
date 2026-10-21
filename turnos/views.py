import json
import re
from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from sedes.models import Sede
from auditoria.registro import foto, registrar
from .models import Turno
from .emails import enviar_cancelacion_turno, enviar_confirmacion_turno, enviar_reprogramacion_turno

import logging
logger = logging.getLogger(__name__)

# ── Configuración ──
MAX_POR_HORARIO = 1
MAX_TURNOS_DIA  = 20
HORA_INICIO     = 9    # Atención de 09:00 a 13:00 hs (último turno 12:45)
HORA_FIN        = 13
MINUTOS_SLOT    = 15

FERIADOS = [
    "01-01","03-03","03-04","04-02","05-01","05-25",
    "06-20","07-09","08-17","10-12","11-20","12-08","12-25"
]

def es_feriado(d):
    return f"{d.month:02d}-{d.day:02d}" in FERIADOS

def es_habil(d):
    if d.weekday() >= 5: return False   # sábado=5, domingo=6
    if es_feriado(d):    return False
    if d < timezone.localdate(): return False
    return True

def slot_ya_paso(d, hora_str):
    """True si el horario es de hoy y ya pasó (no se puede reservar)."""
    if d != timezone.localdate():
        return False
    return hora_str <= timezone.localtime().strftime('%H:%M')


# ── Sedes ──
def sede_central():
    """Sede que recibe los turnos online del sitio (marcada por el Super Admin;
    hoy es la Sede Central)."""
    return Sede.objects.filter(activo=True, recibe_turnos_online=True).order_by('id').first()

def turnos_activos(fecha, sede):
    """Turnos que ocupan lugar en esa fecha y sede.
    Los turnos sin sede asignada (anteriores a este campo) cuentan para la sede de turnos online."""
    qs = Turno.objects.filter(fecha=fecha, estado__in=['pendiente', 'asistio'])
    if sede is None:
        return qs.filter(sede__isnull=True)
    central = sede_central()
    if central and sede.pk == central.pk:
        return qs.filter(Q(sede=sede) | Q(sede__isnull=True))
    return qs.filter(sede=sede)

def obtener_sede(sede_id):
    """Sede activa con ese id, o None si no existe / no está activa."""
    try:
        return Sede.objects.get(pk=int(sede_id), activo=True)
    except (Sede.DoesNotExist, TypeError, ValueError):
        return None


# ── Validaciones de datos del ciudadano ──
RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$")
RE_DNI    = re.compile(r'^\d{7,8}$')
RE_TEL    = re.compile(r'^\+?[\d\s()-]+$')
# El turnero es exclusivo para DNI ('pasaporte' queda en el modelo solo por turnos históricos)
TRAMITES_VALIDOS = {clave for clave, _ in Turno.TRAMITES if clave.startswith('dni-')}

def validar_datos_turno(tramite, nombre, dni, email, telefono, direccion, telefono_obligatorio=True):
    """Devuelve un mensaje de error, o None si los datos son válidos."""
    if tramite not in TRAMITES_VALIDOS:
        return 'El trámite seleccionado no es válido.'
    if not 3 <= len(nombre) <= 100 or not RE_NOMBRE.match(nombre):
        return 'Ingresá un nombre válido (solo letras, entre 3 y 100 caracteres).'
    if len(nombre.split()) < 2:
        return 'Ingresá nombre y apellido.'
    if not RE_DNI.match(dni):
        return 'El DNI debe tener 7 u 8 dígitos, sin puntos.'
    try:
        validate_email(email)
    except ValidationError:
        return 'Ingresá un correo electrónico válido.'
    if telefono or telefono_obligatorio:
        digitos = re.sub(r'\D', '', telefono)
        if not RE_TEL.match(telefono) or not 10 <= len(digitos) <= 13:
            return 'Ingresá un teléfono válido con código de área (ej: 3854123456).'
    if direccion and not 5 <= len(direccion) <= 300:
        return 'La dirección debe tener entre 5 y 300 caracteres.'
    return None

def generar_slots():
    slots = []
    h, m = HORA_INICIO, 0
    while h < HORA_FIN:
        slots.append(f"{h:02d}:{m:02d}")
        m += MINUTOS_SLOT
        if m >= 60:
            m -= 60
            h += 1
    return slots

SLOTS = generar_slots()


# ── API pública — disponibilidad (sin login) ──
def disponibilidad(request):
    fecha_str = request.GET.get('fecha')
    if not fecha_str:
        return JsonResponse({'error': 'Falta el parámetro fecha.'}, status=400)

    try:
        d = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)

    if request.GET.get('sede'):
        sede = obtener_sede(request.GET['sede'])
        if not sede:
            return JsonResponse({'error': 'La sede seleccionada no es válida.'}, status=400)
    else:
        sede = sede_central()

    if not es_habil(d):
        return JsonResponse({'habil': False, 'slots': []})

    turnos_del_dia = turnos_activos(d, sede)
    conteo = {}
    for t in turnos_del_dia:
        hora_key = t.hora.strftime('%H:%M')
        conteo[hora_key] = conteo.get(hora_key, 0) + 1

    total_dia = turnos_del_dia.count()

    slots_info = []
    for slot in SLOTS:
        usados = conteo.get(slot, 0)
        libres = 0 if slot_ya_paso(d, slot) else MAX_POR_HORARIO - usados
        slots_info.append({
            'hora':   slot,
            'libres': max(libres, 0),
            'lleno':  libres <= 0,
        })

    return JsonResponse({
        'habil':     True,
        'habil_dia': total_dia < MAX_TURNOS_DIA and any(not s['lleno'] for s in slots_info),
        'slots':     slots_info,
    })


# ── API pública — crear turno (ciudadano y carga manual del panel) ──
@csrf_exempt
@require_POST
def crear_turno(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    def campo(nombre):
        return str(data.get(nombre) or '').strip()

    tramite   = campo('tramite')
    nombre    = ' '.join(campo('nombre').split())
    dni       = campo('dni').replace('.', '')
    email     = campo('email').lower()
    telefono  = campo('telefono')
    direccion = campo('direccion')
    fecha_str = campo('fecha')
    hora_str  = campo('hora')

    # Solo el personal logueado puede cargar turnos manuales y elegir el estado;
    # un ciudadano siempre crea un turno 'sistema' en estado 'pendiente'.
    es_personal = request.user.is_authenticated and request.user.is_staff
    origen = 'manual' if es_personal and data.get('origen') == 'manual' else 'sistema'
    estado = data.get('estado', 'pendiente') if origen == 'manual' else 'pendiente'
    if estado not in dict(Turno.ESTADOS):
        estado = 'pendiente'

    # Los turnos online van siempre a la Sede Central; en la carga manual
    # el personal puede elegir cualquier sede activa (por defecto, la central).
    if origen == 'manual' and data.get('sede_id'):
        sede = obtener_sede(data.get('sede_id'))
        if not sede:
            return JsonResponse({'error': 'La sede seleccionada no es válida.'}, status=400)
    else:
        sede = sede_central()

    # Para el ciudadano todos los campos son obligatorios;
    # en la carga manual teléfono y dirección son opcionales.
    obligatorios = [tramite, nombre, dni, email, fecha_str, hora_str]
    if origen == 'sistema':
        obligatorios += [telefono, direccion]
    if not all(obligatorios):
        return JsonResponse({'error': 'Completá todos los campos obligatorios.'}, status=400)

    error = validar_datos_turno(
        tramite, nombre, dni, email, telefono, direccion,
        telefono_obligatorio=(origen == 'sistema'),
    )
    if error:
        return JsonResponse({'error': error}, status=400)

    try:
        fecha = date.fromisoformat(fecha_str)
        hora  = datetime.strptime(hora_str, '%H:%M').time()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha u hora inválido.'}, status=400)

    if not es_habil(fecha):
        return JsonResponse({'error': 'La fecha seleccionada no es hábil.'}, status=400)

    if hora_str not in SLOTS:
        return JsonResponse({'error': 'El horario seleccionado no es válido.'}, status=400)

    if slot_ya_paso(fecha, hora_str):
        return JsonResponse({'error': 'Ese horario ya pasó. Elegí otro.'}, status=400)

    activos = turnos_activos(fecha, sede)

    # Verificar disponibilidad en la sede
    if activos.filter(hora=hora).count() >= MAX_POR_HORARIO:
        return JsonResponse({'error': 'Ese horario ya no está disponible. Elegí otro.'}, status=400)

    if activos.count() >= MAX_TURNOS_DIA:
        return JsonResponse({'error': 'No hay más turnos disponibles para ese día.'}, status=400)

    # Un mismo DNI no puede tener dos turnos pendientes el mismo día (en ninguna sede)
    if Turno.objects.filter(fecha=fecha, dni=dni, estado='pendiente').exists():
        return JsonResponse(
            {'error': 'Ya existe un turno pendiente para ese DNI en la fecha elegida.'}, status=400
        )

    turno = Turno.objects.create(
        tramite   = tramite,
        nombre    = nombre,
        dni       = dni,
        email     = email,
        telefono  = telefono,
        direccion = direccion,
        fecha     = fecha,
        hora      = hora,
        sede      = sede,
        origen    = origen,
        estado    = estado,
    )

    if turno.estado == 'pendiente':
        enviar_confirmacion_turno(turno)

    # Los turnos que carga el personal quedan en el registro de actividad
    # (los que pide el ciudadano ya quedan registrados como origen "sistema")
    if origen == 'manual':
        registrar(request, 'crear', 'turnos', turno.id, f'{turno.numero_turno} – {turno.nombre}',
                  {**foto(turno, ['tramite', 'dni', 'fecha', 'hora', 'estado']),
                   'sede': sede.nombre if sede else None})

    return JsonResponse({
        'ok':           True,
        'numero_turno': turno.numero_turno,
        'fecha':        fecha_str,
        'hora':         hora_str,
        'sede':         sede.nombre if sede else '',
    })


# ── API del panel admin ──
@login_required
def listar_turnos(request):
    turnos = Turno.objects.all().select_related('atendido_por', 'sede')
    data   = []
    for t in turnos:
        data.append({
            'id':           t.id,
            'numero_turno': t.numero_turno,
            'tramite':      t.get_tramite_display(),
            'nombre':       t.nombre,
            'dni':          t.dni,
            'email':        t.email,
            'telefono':     t.telefono,
            'fecha':        t.fecha.strftime('%d/%m/%Y'),
            'hora':         t.hora.strftime('%H:%M'),
            'estado':       t.estado,
            'origen':       t.origen,
            'tramite_slug': t.tramite,  # ← el valor raw del modelo (dni-5-8, etc.)
            'sede':         t.sede.nombre if t.sede else '',
            'sede_id':      t.sede_id,
        })
    return JsonResponse({'turnos': data})


@login_required
@require_POST
def cambiar_estado(request, turno_id):
    try:
        data   = json.loads(request.body)
        turno  = Turno.objects.get(id=turno_id)
        estado = data.get('estado')

        estados_validos = ['pendiente', 'asistio', 'no_asistio', 'cancelado']
        if estado not in estados_validos:
            return JsonResponse({'error': 'Estado inválido.'}, status=400)

        estado_anterior = turno.estado
        turno.estado = estado
        if estado in ['asistio', 'no_asistio']:
            turno.atendido_por = request.user
        turno.save()
        if estado != estado_anterior:
            registrar(request, 'estado', 'turnos', turno.id, f'{turno.numero_turno} – {turno.nombre}',
                      {'estado': [estado_anterior, estado]})

        # Notificar al ciudadano si el turno fue cancelado
        if estado == 'cancelado':
            enviar_cancelacion_turno(turno)

        return JsonResponse({'ok': True, 'estado': estado})

    except Turno.DoesNotExist:
        return JsonResponse({'error': 'Turno no encontrado.'}, status=404)
    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)
    
@login_required
@require_POST
def reprogramar_turno(request, turno_id):
    """Permite al personal reprogramar fecha y hora de un turno existente."""
    turno = get_object_or_404(Turno, id=turno_id)
    try:
        data          = json.loads(request.body)
        nueva_fecha_str = data.get('fecha', '').strip()
        nueva_hora_str  = data.get('hora', '').strip()

        if not nueva_fecha_str or not nueva_hora_str:
            return JsonResponse({'error': 'Fecha y hora son obligatorias.'}, status=400)

        try:
            nueva_fecha = date.fromisoformat(nueva_fecha_str)
            nueva_hora  = datetime.strptime(nueva_hora_str, '%H:%M').time()
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha u hora inválido.'}, status=400)

        if not es_habil(nueva_fecha):
            return JsonResponse({'error': 'La fecha seleccionada no es hábil.'}, status=400)

        if nueva_hora_str not in SLOTS:
            return JsonResponse({'error': 'El horario seleccionado no es válido.'}, status=400)

        if slot_ya_paso(nueva_fecha, nueva_hora_str):
            return JsonResponse({'error': 'Ese horario ya pasó. Elegí otro.'}, status=400)

        # Verificar disponibilidad excluyendo el turno actual
        ocupado = turnos_activos(nueva_fecha, turno.sede).filter(
            hora=nueva_hora,
        ).exclude(id=turno_id).count()

        if ocupado >= MAX_POR_HORARIO:
            return JsonResponse(
                {'error': 'Ese horario ya no está disponible. Elegí otro.'}, status=400
            )

        # Guardar valores anteriores para el correo
        fecha_anterior = turno.fecha
        hora_anterior  = turno.hora

        antes = foto(turno, ['fecha', 'hora', 'estado'])
        turno.fecha  = nueva_fecha
        turno.hora   = nueva_hora
        turno.estado = 'pendiente'   # Vuelve a pendiente tras reprogramación
        turno.save()
        registrar(request, 'reprogramar', 'turnos', turno.id, f'{turno.numero_turno} – {turno.nombre}',
                  {c: [antes[c], v] for c, v in foto(turno, ['fecha', 'hora', 'estado']).items() if antes[c] != v})

        # Notificar al ciudadano
        enviar_reprogramacion_turno(turno, fecha_anterior, hora_anterior)

        return JsonResponse({
            'ok':   True,
            'fecha': nueva_fecha_str,
            'hora':  nueva_hora_str,
        })

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
def estadisticas(request):
    hoy     = timezone.localdate()
    hace_7  = hoy - timedelta(days=6)

    # ── Totales generales ──
    total         = Turno.objects.count()
    pendientes    = Turno.objects.filter(estado='pendiente').count()
    asistieron    = Turno.objects.filter(estado='asistio').count()
    no_asistieron = Turno.objects.filter(estado='no_asistio').count()
    cancelados    = Turno.objects.filter(estado='cancelado').count()

    # ── Por origen ──
    sistema = Turno.objects.filter(origen='sistema').count()
    manual  = Turno.objects.filter(origen='manual').count()

    # ── Por trámite ──
    por_tramite = list(
        Turno.objects.values('tramite')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # ── Últimos 7 días — compatible SQLite ──
    ultimos_7 = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        count = Turno.objects.filter(fecha=dia).count()
        ultimos_7.append({'dia': str(dia), 'total': count})

    # ── Tasa de asistencia ──
    atendidos = asistieron + no_asistieron
    tasa_asistencia = round((asistieron / atendidos * 100), 1) if atendidos > 0 else 0

    # ── Hoy ──
    hoy_total      = Turno.objects.filter(fecha=hoy).count()
    hoy_pendientes = Turno.objects.filter(fecha=hoy, estado='pendiente').count()

    return JsonResponse({
        'total':           total,
        'pendientes':      pendientes,
        'asistieron':      asistieron,
        'no_asistieron':   no_asistieron,
        'cancelados':      cancelados,
        'sistema':         sistema,
        'manual':          manual,
        'por_tramite':     por_tramite,
        'ultimos_7':       ultimos_7,
        'tasa_asistencia': tasa_asistencia,
        'hoy_total':       hoy_total,
        'hoy_pendientes':  hoy_pendientes,
    })