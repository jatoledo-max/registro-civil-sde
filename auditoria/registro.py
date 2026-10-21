"""Funciones para dejar constancia de las acciones del personal."""

import logging
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models.fields.files import FieldFile

from .models import RegistroActividad

logger = logging.getLogger(__name__)

LARGO_MAXIMO = 300   # los textos largos (cuerpo de una noticia, requisitos) se recortan


def _valor(v):
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.strftime('%d/%m/%Y %H:%M')
    if isinstance(v, date):
        return v.strftime('%d/%m/%Y')
    if isinstance(v, time):
        return v.strftime('%H:%M')
    if isinstance(v, FieldFile):                        # archivos e imágenes: solo el nombre
        return v.name or None
    texto = str(v)
    return texto if len(texto) <= LARGO_MAXIMO else texto[:LARGO_MAXIMO] + '…'


def foto(obj, campos):
    """Valores actuales de los campos indicados, listos para guardar en JSON."""
    return {c: _valor(getattr(obj, c, None)) for c in campos}


def diferencias(antes, despues):
    """{campo: [antes, después]} solo con lo que cambió."""
    return {c: [antes.get(c), despues.get(c)] for c in despues if antes.get(c) != despues.get(c)}


def ip_de(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = reenviada.split(',')[0].strip() if reenviada else request.META.get('REMOTE_ADDR')
    return ip or None


def registrar(request, accion, modulo, objeto_id='', objeto='', cambios=None, usuario=None):
    """Guarda una línea en la bitácora. Un error acá nunca debe frenar la operación del usuario."""
    try:
        usuario = usuario or (request.user if request.user.is_authenticated else None)
        RegistroActividad.objects.create(
            usuario=usuario,
            usuario_nombre=(usuario.get_full_name() or usuario.username) if usuario else 'Sistema',
            accion=accion,
            modulo=modulo,
            objeto_id=str(objeto_id or ''),
            objeto=str(objeto or '')[:255],
            cambios=cambios or {},
            ip=ip_de(request),
        )
    except Exception:
        logger.exception('No se pudo guardar el registro de actividad')
