from django.contrib.auth.models import User
from django.db import models


class RegistroActividad(models.Model):
    """Bitácora de acciones del personal. Los registros no se editan ni se borran."""

    ACCIONES = [
        ('crear',       'Creó'),
        ('editar',      'Editó'),
        ('eliminar',    'Eliminó'),
        ('estado',      'Cambió el estado'),
        ('reprogramar', 'Reprogramó'),
        ('activar',     'Activó'),
        ('desactivar',  'Desactivó'),
        ('password',    'Cambió la contraseña'),
        ('login',       'Inició sesión'),
        ('logout',      'Cerró sesión'),
    ]
    MODULOS = [
        ('turnos',     'Turnos'),
        ('noticias',   'Noticias'),
        ('tramites',   'Trámites'),
        ('categorias', 'Categorías'),
        ('sedes',      'Sedes'),
        ('usuarios',   'Usuarios'),
        ('sesion',     'Sesión'),
    ]

    fecha          = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='actividad')
    # Copia del nombre: el registro sigue siendo legible aunque el usuario se elimine
    usuario_nombre = models.CharField(max_length=200)
    accion         = models.CharField(max_length=20, choices=ACCIONES)
    modulo         = models.CharField(max_length=20, choices=MODULOS, db_index=True)
    objeto_id      = models.CharField(max_length=40, blank=True)
    objeto         = models.CharField(max_length=255, blank=True)   # descripción legible del registro
    cambios        = models.JSONField(default=dict, blank=True)    # {campo: [antes, después]} o copia al eliminar
    ip             = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Registro de actividad'
        verbose_name_plural = 'Registro de actividad'

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} · {self.usuario_nombre} · {self.get_accion_display()} · {self.objeto}'

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('El registro de actividad no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('El registro de actividad no se puede eliminar.')
