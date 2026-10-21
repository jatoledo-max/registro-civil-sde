from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tramites_app', '0003_tramite_requiere_turno'),
    ]

    operations = [
        migrations.AddField(
            model_name='tramite',
            name='requisitos',
            field=models.TextField(blank=True, help_text='Un requisito por línea.'),
        ),
        migrations.AddField(
            model_name='tramite',
            name='como_se_inicia',
            field=models.TextField(blank=True, help_text='Un paso por línea.'),
        ),
        migrations.AddField(
            model_name='tramite',
            name='modalidad_presencial',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tramite',
            name='modalidad_digital',
            field=models.BooleanField(default=False),
        ),
    ]
