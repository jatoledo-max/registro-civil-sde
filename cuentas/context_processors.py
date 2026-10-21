from django.conf import settings


def sitio(request):
    """Datos que el JavaScript necesita para armar rutas y leer el token CSRF."""
    return {
        'url_base': settings.URL_PREFIX,
        'csrf_cookie_name': settings.CSRF_COOKIE_NAME,
    }
