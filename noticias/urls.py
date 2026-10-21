from django.urls import path
from . import views

urlpatterns = [
    path('api/noticias/',                         views.listar_noticias,  name='api_listar_noticias'),
    path('api/noticias/crear/',                   views.crear_noticia,    name='api_crear_noticia'),
    path('api/noticias/<int:noticia_id>/editar/', views.editar_noticia,   name='api_editar_noticia'),
    path('api/noticias/<int:noticia_id>/eliminar/', views.eliminar_noticia, name='api_eliminar_noticia'),
    path('api/noticias/publicas/',                views.noticias_publicas, name='api_noticias_publicas'),
]