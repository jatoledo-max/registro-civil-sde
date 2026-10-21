from django.urls import path
from . import views

urlpatterns = [
    path('api/usuarios/',views.listar_usuarios,name='listar_usuarios'),
    path('api/usuarios/crear/',views.crear_usuario,name='crear_usuario'),
    path('api/usuarios/<int:user_id>/editar/',views.editar_usuario,name='editar_usuario'),
    path('api/usuarios/<int:user_id>/desactivar/',views.desactivar_usuario,name='desactivar_usuario'),
]