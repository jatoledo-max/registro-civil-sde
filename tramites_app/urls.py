from django.urls import path
from . import views

urlpatterns = [
    path('api/tramites/', views.api_listar_tramites, name='api_listar_tramites'),
    path('api/tramites/crear/',views.api_crear_tramite, name='api_crear_tramite'),
    path('api/tramites/<int:tramite_id>/editar/', views.api_editar_tramite,name='api_editar_tramite'),
    path('api/tramites/<int:tramite_id>/eliminar/',views.api_eliminar_tramite, name='api_eliminar_tramite'),
    path('api/categorias/', views.api_listar_categorias, name='api_listar_categorias'),
    path('api/categorias/crear/', views.api_crear_categoria, name='api_crear_categoria'),
]