# Generated manually because manage.py makemigrations is not available in this environment.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0010_usuario_habilidades_aprendizaje'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuario',
            name='habilidades',
        ),
    ]
