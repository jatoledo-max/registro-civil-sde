from django.urls import path
from . import views

urlpatterns = [
    path('api/turnos/',                              views.listar_turnos,     name='api_listar_turnos'),
    path('api/turnos/crear/',                        views.crear_turno,       name='api_crear_turno'),
    path('api/turnos/<int:turno_id>/estado/',        views.cambiar_estado,    name='api_cambiar_estado'),
    path('api/turnos/<int:turno_id>/reprogramar/',   views.reprogramar_turno, name='api_reprogramar_turno'),
    path('api/turnos/disponibilidad/',               views.disponibilidad,    name='api_disponibilidad'),
    path('api/turnos/estadisticas/',                 views.estadisticas,      name='api_estadisticas_turnos'),
]