from datetime import date, datetime, time

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from usuarios.views import es_superadmin
from .models import RegistroActividad

POR_PAGINA = 50


def _fecha(texto, fin=False):
    try:
        d = date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None
    return timezone.make_aware(datetime.combine(d, time.max if fin else time.min))


@login_required
def listar_actividad(request):
    if not es_superadmin(request.user):
        return JsonResponse({'error': 'Solo un Super Admin puede ver el registro de actividad.'}, status=403)

    qs = RegistroActividad.objects.all()
    g = request.GET
    if g.get('modulo'):
        qs = qs.filter(modulo=g['modulo'])
    if g.get('accion'):
        qs = qs.filter(accion=g['accion'])
    if g.get('usuario'):
        qs = qs.filter(usuario_nombre=g['usuario'])
    if _fecha(g.get('desde')):
        qs = qs.filter(fecha__gte=_fecha(g['desde']))
    if _fecha(g.get('hasta'), fin=True):
        qs = qs.filter(fecha__lte=_fecha(g['hasta'], fin=True))
    if g.get('q'):
        qs = qs.filter(Q(objeto__icontains=g['q']) | Q(usuario_nombre__icontains=g['q']))

    pagina = Paginator(qs, POR_PAGINA).get_page(g.get('pagina') or 1)
    return JsonResponse({
        'registros': [{
            'fecha':   timezone.localtime(r.fecha).strftime('%d/%m/%Y %H:%M:%S'),
            'usuario': r.usuario_nombre,
            'accion':  r.accion,
            'accion_texto': r.get_accion_display(),
            'modulo':  r.get_modulo_display(),
            'objeto':  r.objeto,
            'cambios': r.cambios,
            'ip':      r.ip or '',
        } for r in pagina],
        'pagina':  pagina.number,
        'paginas': pagina.paginator.num_pages,
        'total':   pagina.paginator.count,
        'usuarios': sorted(set(RegistroActividad.objects.values_list('usuario_nombre', flat=True))),
        'modulos':  RegistroActividad.MODULOS,
        'acciones': RegistroActividad.ACCIONES,
    })
