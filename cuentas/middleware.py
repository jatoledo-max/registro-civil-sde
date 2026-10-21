from django.http import JsonResponse
from django.shortcuts import redirect

# Rutas públicas que siguen funcionando aunque el usuario deba cambiar su contraseña
API_PUBLICAS = (
    '/api/turnos/disponibilidad/', '/api/turnos/crear/',
    '/api/chatbot/', '/api/noticias/publicas/',
)


def debe_cambiar_password(user):
    perfil = getattr(user, 'perfil', None)
    return bool(perfil and perfil.debe_cambiar_password)


class CambioPasswordObligatorioMiddleware:
    """Si la contraseña la asignó otra persona (alta o blanqueo), el usuario no puede
    usar el panel ni la API interna hasta elegir una propia."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta = request.path_info   # sin el prefijo del subdirectorio
        protegida = (
            ruta.startswith(('/admin-panel/', '/admin/'))
            or (ruta.startswith('/api/') and not ruta.startswith(API_PUBLICAS))
        )
        if protegida and request.user.is_authenticated and debe_cambiar_password(request.user):
            if ruta.startswith('/api/'):
                return JsonResponse(
                    {'error': 'Tenés que cambiar tu contraseña antes de continuar.'}, status=403
                )
            return redirect('cambiar_password')
        return self.get_response(request)
