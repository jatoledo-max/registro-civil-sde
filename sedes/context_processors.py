from django.utils.functional import SimpleLazyObject


def sede_turnos(request):
    """Expone en los templates la sede que recibe los turnos online ({{ sede_turnos }})."""
    def obtener():
        from turnos.views import sede_central
        return sede_central()
    return {'sede_turnos': SimpleLazyObject(obtener)}
