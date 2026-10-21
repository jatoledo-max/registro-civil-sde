import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from auditoria.registro import diferencias, foto, registrar
from .models import Noticia

CAMPOS_AUDITADOS = ['titulo', 'cuerpo', 'tag', 'estado', 'imagen']

import logging
from usuarios.views import es_superadmin
logger = logging.getLogger(__name__)

TAGS_VALIDOS    = {clave for clave, _ in Noticia.TAGS}
ESTADOS_VALIDOS = {clave for clave, _ in Noticia.ESTADOS}
IMAGEN_MAX_MB   = 5
IMAGEN_TIPOS    = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


def validar_noticia(titulo, cuerpo, tag, estado, imagen):
    """Devuelve un mensaje de error o None."""
    if not titulo or not cuerpo:
        return 'Título y cuerpo son obligatorios.'
    if len(titulo) > 200:
        return 'El título no puede superar los 200 caracteres.'
    if tag not in TAGS_VALIDOS:
        return 'Categoría inválida.'
    if estado not in ESTADOS_VALIDOS:
        return 'Estado inválido.'
    if imagen:
        if imagen.content_type not in IMAGEN_TIPOS:
            return 'La imagen debe ser JPG, PNG, WEBP o GIF.'
        if imagen.size > IMAGEN_MAX_MB * 1024 * 1024:
            return f'La imagen no puede superar los {IMAGEN_MAX_MB} MB.'
        try:
            from PIL import Image
            Image.open(imagen).verify()
            imagen.seek(0)
        except Exception:
            return 'El archivo no es una imagen válida.'
    return None

IMAGEN_DEFAULT = 'https://i.pinimg.com/736x/8c/c2/b2/8cc2b2e8191e930d298607a299fb92c8.jpg'

MESES_ES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]


def format_fecha_publica(fecha):
    if not fecha:
        return ''
    return f"{fecha.day} de {MESES_ES[fecha.month - 1]} de {fecha.year}"


def get_imagen_url(noticia, request):
    if noticia.imagen:
        return noticia.imagen.url
    return IMAGEN_DEFAULT


@login_required
def listar_noticias(request):
    noticias = Noticia.objects.select_related('creado_por', 'aprobado_por').all()
    data = []
    for n in noticias:
        data.append({
            'id':          n.id,
            'titulo':      n.titulo,
            'cuerpo':      n.cuerpo,
            'tag':         n.tag,
            'imagen':      get_imagen_url(n, request),
            'estado':      n.estado,
            'creado_por':  n.creado_por.get_full_name() if n.creado_por else 'Sistema',
            'fecha':       n.fecha_creacion.strftime('%d/%m/%Y'),
        })
    return JsonResponse({'noticias': data})


def noticias_publicas(request):
    noticias = Noticia.objects.filter(estado='publicada').order_by('-fecha_publicacion')[:6]
    data = []
    for n in noticias:
        data.append({
            'id':     n.id,
            'titulo': n.titulo,
            'cuerpo': n.cuerpo,
            'tag':    n.tag,
            'imagen': get_imagen_url(n, request),
            'fecha':  format_fecha_publica(n.fecha_publicacion),
        })
    return JsonResponse({'noticias': data})


@login_required
def crear_noticia(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    try:
        titulo = request.POST.get('titulo', '').strip()
        cuerpo = request.POST.get('cuerpo', '').strip()
        tag    = request.POST.get('tag', 'General').strip()
        estado = request.POST.get('estado', 'borrador').strip()

        error = validar_noticia(titulo, cuerpo, tag, estado, request.FILES.get('imagen'))
        if error:
            return JsonResponse({'error': error}, status=400)

        # Solo superadmin puede publicar directamente
        if estado == 'publicada' and not es_superadmin(request.user):
            estado = 'revision'

        noticia = Noticia(
            titulo     = titulo,
            cuerpo     = cuerpo,
            tag        = tag,
            estado     = estado,
            creado_por = request.user,
        )

        if estado == 'publicada':
            noticia.fecha_publicacion = timezone.now()
            noticia.aprobado_por      = request.user

        if 'imagen' in request.FILES:
            noticia.imagen = request.FILES['imagen']

        noticia.save()
        registrar(request, 'crear', 'noticias', noticia.id, noticia.titulo,
                  foto(noticia, CAMPOS_AUDITADOS))
        return JsonResponse({'ok': True, 'id': noticia.id})

    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
def editar_noticia(request, noticia_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    try:
        noticia = Noticia.objects.get(id=noticia_id)
        antes = foto(noticia, CAMPOS_AUDITADOS)

        titulo = request.POST.get('titulo', noticia.titulo).strip()
        cuerpo = request.POST.get('cuerpo', noticia.cuerpo).strip()
        tag    = request.POST.get('tag', noticia.tag).strip()
        estado = request.POST.get('estado', noticia.estado).strip()

        error = validar_noticia(titulo, cuerpo, tag, estado, request.FILES.get('imagen'))
        if error:
            return JsonResponse({'error': error}, status=400)

        if not es_superadmin(request.user) and estado == 'publicada':
            estado = noticia.estado

        noticia.titulo = titulo
        noticia.cuerpo = cuerpo
        noticia.tag    = tag

        if estado != noticia.estado:
            noticia.estado = estado
            if estado == 'publicada' and not noticia.fecha_publicacion:
                noticia.fecha_publicacion = timezone.now()
                noticia.aprobado_por      = request.user

        if 'imagen' in request.FILES:
            noticia.imagen = request.FILES['imagen']

        noticia.save()
        cambios = diferencias(antes, foto(noticia, CAMPOS_AUDITADOS))
        if cambios:
            registrar(request, 'editar', 'noticias', noticia.id, noticia.titulo, cambios)
        return JsonResponse({'ok': True})

    except Noticia.DoesNotExist:
        return JsonResponse({'error': 'Noticia no encontrada.'}, status=404)
    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)


@login_required
@require_POST
def eliminar_noticia(request, noticia_id):
    try:
        if not es_superadmin(request.user):
            return JsonResponse({'error': 'Sin permisos.'}, status=403)
        noticia = Noticia.objects.get(id=noticia_id)
        copia = foto(noticia, CAMPOS_AUDITADOS)
        noticia.delete()
        registrar(request, 'eliminar', 'noticias', noticia_id, copia['titulo'], copia)
        return JsonResponse({'ok': True})
    except Noticia.DoesNotExist:
        return JsonResponse({'error': 'Noticia no encontrada.'}, status=404)
    except Exception as e:
        logger.exception('Error en %s', request.path)
        return JsonResponse({'error': 'Ocurrió un error inesperado. Intentá de nuevo.'}, status=500)