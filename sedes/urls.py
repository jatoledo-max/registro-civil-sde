from django.urls import path
from . import views

urlpatterns = [
    path('api/sedes/',views.listar_sedes,name='listar_sedes'),
    path('api/sedes/crear/',views.crear_sede,name='crear_sede'),
    path('api/sedes/<int:sede_id>/editar/', views.editar_sede,name='editar_sede'),
    path('api/sedes/<int:sede_id>/eliminar/', views.eliminar_sede, name='eliminar_sede'),
]