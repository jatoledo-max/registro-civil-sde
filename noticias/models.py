from django.db import models
from django.contrib.auth.models import User


class Noticia(models.Model):

    ESTADOS = [
        ('borrador',   'Borrador'),
        ('revision',   'En revisión'),
        ('publicada',  'Publicada'),
        ('archivada',  'Archivada'),
    ]

    TAGS = [
        ('Institucional',  'Institucional'),
        ('Trámites',       'Trámites'),
        ('Digitalización', 'Digitalización'),
        ('Eventos',        'Eventos'),
        ('General',        'General'),
    ]

    titulo      = models.CharField(max_length=200)
    cuerpo      = models.TextField()
    tag         = models.CharField(max_length=50, choices=TAGS, default='General')
    imagen      = models.ImageField(upload_to='noticias/', null=True, blank=True)
    estado      = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    creado_por  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='noticias_creadas'
    )
    aprobado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='noticias_aprobadas'
    )
    fecha_creacion    = models.DateTimeField(auto_now_add=True)
    fecha_publicacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.titulo} [{self.get_estado_display()}]"

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
