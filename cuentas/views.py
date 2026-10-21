from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from tramites_app.views import lista_tramites as tramites
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
from django.core.cache import cache
from tramites_app.models import Tramite as TramiteModel
from usuarios.views import es_superadmin
from auditoria.registro import registrar
import os, json, logging
from groq import Groq

logger = logging.getLogger(__name__)

def login_bloqueado(request, credentials=None, *args, **kwargs):
    """Respuesta de django-axes tras varios intentos fallidos."""
    return render(request, 'login.html', {
        'error': 'Demasiados intentos fallidos. Por seguridad, esperá 15 minutos antes de volver a intentar.',
        'username': (credentials or {}).get('username', '') if isinstance(credentials, dict) else '',
    }, status=429)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('admin_panel')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            return render(request, 'login.html', {
                'error': 'Ingresá tu usuario y contraseña.', 'username': username,
            })

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_active and user.is_staff:
            login(request, user)
            registrar(request, 'login', 'sesion', user.id, user.get_full_name() or user.username)
            return redirect('admin_panel')
        elif user is not None and not user.is_staff:
            error = 'No tenés permisos para acceder al panel.'
        elif user is not None and not user.is_active:
            error = 'Tu usuario está desactivado.'
        else:
            error = 'Usuario o contraseña incorrectos.'
        return render(request, 'login.html', {'error': error, 'username': username})

    return render(request, 'login.html')


@login_required
def admin_panel(request):
    rol = 'super_admin' if es_superadmin(request.user) else 'operador'

    from sedes.models import Sede
    from turnos.views import sede_central
    central = sede_central()

    return render(request, 'admin.html', {
        'es_superadmin': rol == 'super_admin',
        'usuario': request.user,
        'rol': rol,
        # Sedes activas para la carga manual de turnos (por defecto, la central)
        'sedes_turnos': Sede.objects.filter(activo=True).order_by('nombre'),
        'sede_central_id': central.id if central else None,
    })


@login_required
def cambiar_password(request):
    """El usuario elige su propia contraseña. Es obligatorio cuando la cuenta la creó
    o la blanqueó otra persona, así la contraseña final solo la conoce su dueño."""
    if not request.user.is_staff:
        return redirect('login')

    perfil = getattr(request.user, 'perfil', None)
    obligatorio = bool(perfil and perfil.debe_cambiar_password)

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)   # no cerrar la sesión actual
            registrar(request, 'password', 'usuarios', user.id, user.get_full_name() or user.username,
                      {'contraseña': ['(oculta)', 'cambiada por el propio usuario']})
            if perfil:
                perfil.debe_cambiar_password = False
                perfil.save(update_fields=['debe_cambiar_password'])
            return redirect(f"{reverse('admin_panel')}?password=actualizada")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'cambiar_password.html', {'form': form, 'obligatorio': obligatorio})


def logout_view(request):
    if request.user.is_authenticated:
        registrar(request, 'logout', 'sesion', request.user.id,
                  request.user.get_full_name() or request.user.username)
    logout(request)
    return redirect('login')


def inicio(request):
    return render(request, 'index-1.html')


@login_required
def usuario_actual(request):
    return JsonResponse({
        'username': request.user.username,
        'nombre':   request.user.get_full_name() or request.user.username,
        'email':    request.user.email,
        'rol':      'super_admin' if es_superadmin(request.user) else 'operador',
    })

def identificacion(request):
    return render(request, 'identificacion.html')

def tramites(request):
    return render(request, 'tramites.html')

def tramite_detalle(request, slug):
    try:
        get_template(f'tramites/{slug}.html')
        return render(request, f'tramites/{slug}.html')
    except TemplateDoesNotExist:
        # Si no existe, usá el template genérico con datos del modelo
        tramite = get_object_or_404(TramiteModel, slug=slug, estado='publicado')
        return render(request, 'tramites/detalle_generico.html', {'tramite': tramite})

def mision(request):
    return render(request, 'mision.html')

def nacimiento(request):
    return render(request, 'nacimiento.html')

def defuncion(request):
    return render(request, 'defuncion.html')

def matrimonio(request):
    return render(request, 'matrimonio.html')

from sedes.models import Sede

def sedes(request):
    sedes_activas = Sede.objects.filter(activo=True).values(
        'id', 'nombre', 'direccion', 'departamento', 'provincia', 'horario', 'latitud', 'longitud',
        'referencia', 'recibe_turnos_online',
    )
    sedes_list = []
    for s in sedes_activas:
        sedes_list.append({
            'id':           s['id'],
            'nombre':       s['nombre'],
            'direccion':    s['direccion'],
            'departamento': s['departamento'],
            'provincia':    s['provincia'],
            'horario':      s['horario'],
            'referencia':   s['referencia'],
            'turnos_online': s['recibe_turnos_online'],
            'lat':          float(s['latitud'])  if s['latitud']  else None,
            'lng':          float(s['longitud']) if s['longitud'] else None,
        })

    return render(request, 'sedes.html', {'sedes': sedes_list})




# ══════════════════════════════════════════════════════
#  Chatbot RegIna (Groq)
# ══════════════════════════════════════════════════════

# llama-3.3-70b-versatile fue dado de baja por Groq el 16/08/2026.
# Se puede cambiar el modelo sin tocar código con la variable GROQ_MODEL.
CHATBOT_MODELO_DEFAULT = 'openai/gpt-oss-120b'
CHATBOT_MAX_MENSAJE    = 500
CHATBOT_MAX_HISTORIAL  = 8      # mensajes previos que se envían como contexto
CHATBOT_LIMITE_MINUTO  = 12     # consultas por minuto por IP

CHATBOT_PROMPT_BASE = """
Sos RegIna, la asistente virtual del Registro Civil de Santiago del Estero, Argentina.
Ayudás a los ciudadanos con información sobre trámites, turnos, requisitos y sedes.

Información general:
- Atención al público: lunes a viernes de 09:00 a 13:00 hs. No se atiende sábados, domingos ni feriados.
- Los turnos de DNI se solicitan desde este sitio web con el botón "Solicitar turno" (en la página de cada trámite de DNI o en el carrusel del inicio).
  Se elige el trámite, se completan los datos personales y se elige fecha y horario (turnos cada 15 minutos, de 09:00 a 12:45).
  Se recibe un correo de confirmación con el número de turno. Hay que presentarse con el DNI.
- El turno online es exclusivo para trámites de DNI (actualización 5-8 años, actualización 14 años, cambio de domicilio, nuevo ejemplar) y es opcional.
- El pasaporte NO se puede tramitar con turno online: se gestiona de forma presencial en el Registro Civil.
- Inscripción de nacimiento: dentro de los 40 días corridos del nacimiento. Documentación: certificado médico de nacimiento, DNI de ambos progenitores y libreta de familia si están casados.
- Matrimonio civil: DNI de ambos contrayentes, partidas de nacimiento y dos testigos mayores de edad con DNI.
- Defunción: certificado médico de defunción y DNI de la persona fallecida.
- Las copias de actas se piden en cualquier sede con DNI o por Mi Argentina / Trámites a Distancia (TAD).
{datos}
Reglas:
- Respondé siempre en español rioplatense, de forma clara, amable y breve (máximo 120 palabras).
- Podés usar **negrita** y listas con guiones. No uses tablas ni encabezados.
- Si no sabés algo con certeza, no lo inventes: sugerí acercarse a la sede más cercana.
- No pidas ni guardes datos personales (DNI, teléfono, etc.). Para sacar un turno, indicá usar el formulario del sitio.
- Si la consulta no tiene relación con el Registro Civil, decí amablemente que solo podés ayudar con esos temas.
"""


def _chatbot_datos_dinamicos():
    """Trámites publicados y sedes activas cargados en el sistema."""
    from sedes.models import Sede

    lineas = []
    tramites = TramiteModel.objects.filter(estado='publicado')[:20]
    if tramites:
        lineas.append('Trámites publicados en el sitio:')
        for t in tramites:
            costo = 'gratuito' if t.es_gratuito else (f'${t.precio:,.0f}'.replace(',', '.') if t.precio else 'consultar costo')
            turno = 'requiere turno' if t.requiere_turno else 'sin turno previo'
            requisitos = '; '.join(r.strip() for r in t.requisitos.splitlines() if r.strip())[:300]
            linea = f'- {t.nombre} ({costo}, {turno})'
            if requisitos:
                linea += f'. Requisitos: {requisitos}'
            lineas.append(linea)

    sedes_activas = Sede.objects.filter(activo=True)[:20]
    if sedes_activas:
        lineas.append('Sedes del Registro Civil:')
        for s in sedes_activas:
            linea = f'- {s.nombre}: {s.direccion}, {s.departamento}. Horario: {s.horario}'
            if s.referencia:
                linea += f'. Referencia: {s.referencia}'
            if s.recibe_turnos_online:
                linea += '. Es la sede que atiende los turnos online de DNI'
            lineas.append(linea)

    return ('\n' + '\n'.join(lineas) + '\n') if lineas else ''


def _chatbot_ip(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return reenviada.split(',')[0].strip() if reenviada else request.META.get('REMOTE_ADDR', '')


@csrf_exempt
@require_POST
def chatbot_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    mensaje = str(data.get('mensaje') or '').strip()
    if not mensaje:
        return JsonResponse({'error': 'El mensaje no puede estar vacío.'}, status=400)
    if len(mensaje) > CHATBOT_MAX_MENSAJE:
        return JsonResponse(
            {'error': f'El mensaje es demasiado largo (máximo {CHATBOT_MAX_MENSAJE} caracteres).'}, status=400
        )

    # Límite simple de consultas por minuto para evitar abuso de la API
    clave = f'chatbot:{_chatbot_ip(request)}'
    consultas = cache.get(clave, 0)
    if consultas >= CHATBOT_LIMITE_MINUTO:
        return JsonResponse(
            {'error': 'Hiciste muchas consultas seguidas. Esperá un minuto e intentá de nuevo.'}, status=429
        )
    cache.set(clave, consultas + 1, 60)

    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        return JsonResponse({'respuesta': 'El asistente no está disponible en este momento. '
                                          'Podés consultar la sección Trámites o acercarte a una sede.'})

    # Historial reciente de la conversación (lo arma el navegador)
    historial = []
    for item in (data.get('historial') or [])[-CHATBOT_MAX_HISTORIAL:]:
        if isinstance(item, dict) and item.get('role') in ('user', 'assistant'):
            contenido = str(item.get('content') or '').strip()[:1000]
            if contenido:
                historial.append({'role': item['role'], 'content': contenido})

    system_prompt = CHATBOT_PROMPT_BASE.format(datos=_chatbot_datos_dinamicos())
    modelo = os.environ.get('GROQ_MODEL', CHATBOT_MODELO_DEFAULT)

    opciones = {}
    if modelo.startswith('openai/gpt-oss'):
        # Modelos de razonamiento: pensar poco y no devolver el razonamiento
        opciones['extra_body'] = {'reasoning_effort': 'low', 'include_reasoning': False}

    try:
        client = Groq(api_key=api_key, timeout=20, max_retries=1)
        response = client.chat.completions.create(
            model=modelo,
            messages=[{'role': 'system', 'content': system_prompt}, *historial,
                      {'role': 'user', 'content': mensaje}],
            max_tokens=1024,
            temperature=0.3,
            **opciones,
        )
        respuesta = (response.choices[0].message.content or '').strip()
        if not respuesta:
            raise ValueError('Respuesta vacía del modelo')
    except Exception:
        logger.exception('Error al consultar Groq (modelo %s)', modelo)
        return JsonResponse({
            'respuesta': 'Hubo un problema al procesar tu consulta. Intentá de nuevo en unos momentos.'
        }, status=502)

    return JsonResponse({'respuesta': respuesta})
