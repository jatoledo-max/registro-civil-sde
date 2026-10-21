"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

_django = get_wsgi_application()


def application(environ, start_response):
    """Publicación en un subdirectorio: funciona tanto si el proxy le pasa la ruta completa
    (/registro-civil/sedes/) como si ya le quitó el prefijo (/sedes/)."""
    from django.conf import settings
    prefijo = settings.URL_PREFIX
    if prefijo:
        ruta = environ.get('PATH_INFO', '')
        if ruta == prefijo or ruta.startswith(prefijo + '/'):
            environ['PATH_INFO'] = ruta[len(prefijo):] or '/'
        environ['SCRIPT_NAME'] = prefijo
    return _django(environ, start_response)
