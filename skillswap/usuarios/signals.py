from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import (
    Notificacion,
    NotificacionTipo,
    SolicitudMatch,
    SolicitudMatchEstado,
)


@receiver(pre_save, sender=SolicitudMatch)
def cache_estado_previo(sender, instance, **kwargs):
    if not instance.pk:
        instance._estado_previo = None
        return
    instance._estado_previo = (
        sender.objects.filter(pk=instance.pk).values_list("estado", flat=True).first()
    )


@receiver(post_save, sender=SolicitudMatch)
def crear_notificacion_solicitud_match(sender, instance, created, **kwargs):
    if not created:
        return

    titulo = f"{instance.emisor} quiere hacer match contigo"
    Notificacion.objects.create(
        titulo=titulo,
        tipo=NotificacionTipo.SOLICITUD_MATCH,
        contexto=instance,
        usuario=instance.recipiente,
        mostrar=True,
    )


@receiver(post_save, sender=SolicitudMatch)
def notificar_respuesta_solicitud_match(sender, instance, created, **kwargs):
    if created:
        return

    estado_previo = getattr(instance, "_estado_previo", None)
    if estado_previo == instance.estado:
        return

    if instance.estado == SolicitudMatchEstado.ACEPTADO:
        titulo = f"{instance.recipiente} aceptó tu solicitud de match"
    elif instance.estado == SolicitudMatchEstado.RECHAZADO:
        titulo = f"{instance.recipiente} rechazó tu solicitud de match"
    else:
        return

    Notificacion.objects.create(
        titulo=titulo,
        tipo=NotificacionTipo.SOLICITUD_MATCH,
        contexto=instance,
        usuario=instance.emisor,
        mostrar=True,
    )
