from django.urls import path

from . import views

urlpatterns = [
    path('api/actividad/', views.listar_actividad, name='api_actividad'),
]
