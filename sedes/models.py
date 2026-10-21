from django.db import models
from django.contrib.auth.models import User

class Sede(models.Model):
    nombre       = models.CharField(max_length=100)
    direccion    = models.CharField(max_length=200)
    departamento = models.CharField(max_length=100)
    provincia    = models.CharField(max_length=100, default='Santiago del Estero')
    horario      = models.CharField(max_length=200)
    # Texto de ayuda para el ciudadano (ej: "Esquina Andes y Belgrano Norte, frente a la plaza")
    referencia   = models.CharField(max_length=200, blank=True)
    # Sede que recibe los turnos online del sitio (por ahora solo una a la vez)
    recibe_turnos_online = models.BooleanField(default=False)
    latitud      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    activo       = models.BooleanField(default=False)
    creado_por   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} — {self.departamento}"

    class Meta:
        ordering = ['departamento', 'nombre']
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'