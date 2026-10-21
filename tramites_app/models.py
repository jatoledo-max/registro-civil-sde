from django.db import models
from django.contrib.auth.models import User

class CategoriaTramite(models.Model):
    nombre = models.CharField(max_length=100)
    icono  = models.CharField(max_length=50, default='bi-file-earmark')
    orden  = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'


class Tramite(models.Model):

    ESTADOS = [
        ('borrador',   'Borrador'),
        ('revision',   'En revisión'),
        ('publicado',  'Publicado'),
        ('archivado',  'Archivado'),
    ]

    categoria    = models.ForeignKey(CategoriaTramite, on_delete=models.SET_NULL, null=True, related_name='tramites')
    nombre       = models.CharField(max_length=200)
    descripcion  = models.TextField(blank=True)
    slug         = models.SlugField(max_length=100, unique=True)
    precio       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    es_gratuito          = models.BooleanField(default=False)
    requiere_turno       = models.BooleanField(default=False)
    requisitos           = models.TextField(blank=True, help_text='Un requisito por línea.')
    como_se_inicia       = models.TextField(blank=True, help_text='Un paso por línea.')
    modalidad_presencial = models.BooleanField(default=False)
    modalidad_digital    = models.BooleanField(default=False)
    icono        = models.CharField(max_length=50, default='bi-file-earmark-text')
    estado       = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    creado_por   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tramites_creados')
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tramites_aprobados')
    fecha_creacion   = models.DateTimeField(auto_now_add=True)
    fecha_publicacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} [{self.get_estado_display()}]"

    class Meta:
        ordering = ['categoria__orden', 'nombre']
        verbose_name = 'Trámite'
        verbose_name_plural = 'Trámites'