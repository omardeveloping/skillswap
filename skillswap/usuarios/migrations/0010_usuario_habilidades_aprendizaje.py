# Generated manually because manage.py makemigrations was unavailable in this environment.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_usuario_telefono'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='habilidades_por_aprender',
            field=models.ManyToManyField(
                blank=True,
                help_text='Selecciona las habilidades que quieres aprender.',
                related_name='usuarios_que_quieren_aprender',
                to='usuarios.habilidad',
                verbose_name='habilidades que se quieren aprender',
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='habilidades_que_se_saben',
            field=models.ManyToManyField(
                blank=True,
                help_text='Selecciona las habilidades que dominas.',
                related_name='usuarios_que_saben',
                to='usuarios.habilidad',
                verbose_name='habilidades que se saben',
            ),
        ),
    ]
