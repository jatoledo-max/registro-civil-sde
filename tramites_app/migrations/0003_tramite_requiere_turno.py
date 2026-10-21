from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tramites_app', '0002_tramite_es_gratuito_tramite_precio'),
    ]

    operations = [
        migrations.AddField(
            model_name='tramite',
            name='requiere_turno',
            field=models.BooleanField(default=False),
        ),
    ]
