from django.db import models

# Create your models here.
class conversacion(models.Model):
    participantes = models.ManyToManyField('usuarios.Usuario', related_name='conversaciones')
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversación {self.id} - Participantes: {', '.join([str(p) for p in self.participantes.all()])}"
    
class mensaje(models.Model):
    conversacion = models.ForeignKey(conversacion, related_name='mensajes', on_delete=models.CASCADE)
    remitente = models.ForeignKey('usuarios.Usuario', related_name='mensajes_enviados', on_delete=models.CASCADE)
    contenido = models.TextField()
    leido = models.BooleanField(default=False)
    enviado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensaje {self.id} de {self.remitente} en Conversación {self.conversacion.id}"