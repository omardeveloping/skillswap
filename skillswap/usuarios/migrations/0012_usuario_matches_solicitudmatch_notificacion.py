from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0011_remove_usuario_habilidades'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('indefinido', 'Indefinido'), ('aceptado', 'Aceptado'), ('rechazado', 'Rechazado')], default='indefinido', max_length=15)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('emisor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_enviadas', to=settings.AUTH_USER_MODEL)),
                ('recipiente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_recibidas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=~models.Q(emisor=models.F('recipiente')), name='solicitud_match_sin_autosolicitud')],
            },
        ),
        migrations.AddField(
            model_name='usuario',
            name='matches',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('tipo', models.CharField(choices=[('solicitud_match', 'Solicitud de match')], max_length=50)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('leido', models.BooleanField(default=False)),
                ('mostrar', models.BooleanField(default=True)),
                ('contexto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='usuarios.solicitudmatch')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha', '-id'],
            },
        ),
    ]
