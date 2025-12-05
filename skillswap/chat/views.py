from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from usuarios.models import Usuario
from .models import conversacion, mensaje
from .serializers import ConversacionSerializer, MensajeSerializer


class ConversacionViewSet(viewsets.ModelViewSet):
    """
    Maneja las conversaciones del usuario autenticado y sus mensajes relacionados.
    Incluye acciones para listar, ver mensajes y enviar mensajes en una conversación.
    """

    serializer_class = ConversacionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return (
            conversacion.objects.filter(participantes=user)
            .prefetch_related("participantes")
            .order_by("-fecha_actualizacion", "-id")
        )

    def get_serializer_class(self):
        if self.action in {"mensajes", "enviar"}:
            return MensajeSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        # Asegura que el creador siempre quede agregado a la conversación.
        participantes_ids = self.request.data.get("participantes", [])
        if isinstance(participantes_ids, str):
            participantes_ids = [pk for pk in participantes_ids.split(",") if pk]

        participantes_qs = Usuario.objects.filter(pk__in=participantes_ids)
        nueva_conversacion = serializer.save()
        nueva_conversacion.participantes.add(self.request.user, *participantes_qs)
        nueva_conversacion.save(update_fields=["fecha_actualizacion"])

    @action(detail=True, methods=["get"], url_path="mensajes")
    def mensajes(self, request, pk=None):
        conversacion_obj = self.get_object()
        mensajes_qs = conversacion_obj.mensajes.select_related("remitente").order_by("enviado_en", "id")

        since = request.query_params.get("since")
        if since:
            parsed_since = parse_datetime(since)
            if parsed_since is None:
                return Response(
                    {"detail": "Parámetro 'since' inválido. Usa formato ISO 8601."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if timezone.is_naive(parsed_since):
                parsed_since = timezone.make_aware(parsed_since, timezone.get_default_timezone())
            mensajes_qs = mensajes_qs.filter(enviado_en__gt=parsed_since)

        serializer = self.get_serializer(mensajes_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="enviar")
    def enviar(self, request, pk=None):
        conversacion_obj = self.get_object()
        contenido = request.data.get("contenido", "").strip()

        if not contenido:
            return Response(
                {"detail": "El contenido del mensaje es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nuevo_mensaje = mensaje.objects.create(
            conversacion=conversacion_obj,
            remitente=request.user,
            contenido=contenido,
        )

        conversacion_obj.fecha_actualizacion = timezone.now()
        conversacion_obj.save(update_fields=["fecha_actualizacion"])

        serializer = self.get_serializer(nuevo_mensaje)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
