from django.db import models
from django.contrib.auth.models import User


class Turno(models.Model):

    # ── Estados ──
    ESTADOS = [
        ('pendiente',   'Pendiente'),
        ('asistio',     'Asistió'),
        ('no_asistio',  'No asistió'),
        ('cancelado',   'Cancelado'),
    ]

    # ── Origen ──
    ORIGENES = [
        ('sistema', 'Sistema — solicitado por el ciudadano'),
        ('manual',  'Manual — cargado por empleado'),
    ]

    # ── Trámites disponibles ──
    TRAMITES = [
        ('dni-5-8',       'DNI – Actualización 5-8 años'),
        ('dni-14',        'DNI – Actualización 14 años'),
        ('dni-domicilio', 'DNI – Cambio de domicilio'),
        ('dni-nuevo',     'DNI – Nuevo ejemplar'),
        ('pasaporte',     'Pasaporte'),
    ]

    # ── Número de turno correlativo ──
    numero_turno = models.CharField(max_length=10, unique=True, editable=False)

    # ── Trámite ──
    tramite = models.CharField(max_length=20, choices=TRAMITES)

    # ── Datos del ciudadano ──
    nombre    = models.CharField(max_length=200)
    dni       = models.CharField(max_length=8)
    email     = models.EmailField()
    telefono  = models.CharField(max_length=20)
    direccion = models.CharField(max_length=300)

    # ── Sede donde se atiende el turno ──
    # Por ahora solo la Sede Central recibe turnos online; el personal puede
    # cargar turnos manuales en cualquier sede activa.
    sede = models.ForeignKey(
        'sedes.Sede', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='turnos'
    )

    # ── Fecha y hora ──
    fecha = models.DateField()
    hora  = models.TimeField()

    # ── Estado y origen ──
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    origen = models.CharField(max_length=10, choices=ORIGENES, default='sistema')

    # ── Auditoría ──
    creado_en   = models.DateTimeField(auto_now_add=True)
    atendido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='turnos_atendidos'
    )

    def save(self, *args, **kwargs):
        # Generar número correlativo automático: T-001, T-002...
        if not self.numero_turno:
            ultimo = Turno.objects.order_by('-id').first()
            siguiente = (ultimo.id + 1) if ultimo else 1
            self.numero_turno = f'T-{siguiente:03d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_turno} — {self.nombre} ({self.get_tramite_display()})"

    class Meta:
        ordering = ['fecha', 'hora']
        verbose_name = 'Turno'
        verbose_name_plural = 'Turnos'