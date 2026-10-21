from django.contrib import admin

from .models import RegistroActividad


@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    """Solo lectura: la bitácora no se modifica ni desde el admin de Django."""
    list_display = ('fecha', 'usuario_nombre', 'accion', 'modulo', 'objeto')
    list_filter = ('modulo', 'accion')
    search_fields = ('usuario_nombre', 'objeto')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
