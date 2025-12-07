import json
import logging
import asyncio

from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, renderer_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from asgiref.sync import sync_to_async

from usuarios.models import Usuario
from .models import conversacion, mensaje
from .serializers import ConversacionSerializer, MensajeSerializer

logger = logging.getLogger(__name__)


# ============================
# Event Stream Renderer (DRF)
# ============================
class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = None

    def render(self, data, media_type=None, renderer_context=None):
        return data


# ============================
# Conversacion ViewSet
# ============================
class ConversacionViewSet(viewsets.ModelViewSet):
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
        participantes_ids = self.request.data.get("participantes", [])
        if isinstance(participantes_ids, str):
            participantes_ids = [pk for pk in participantes_ids.split(",") if pk]

        if not participantes_ids:
            raise ValidationError({"participantes": "Debes incluir al menos un participante para iniciar el chat."})

        participantes_qs = Usuario.objects.filter(pk__in=participantes_ids)
        if participantes_qs.count() != len(participantes_ids):
            raise ValidationError({"participantes": "Uno o más participantes no existen."})

        usuario = self.request.user
        for participante in participantes_qs:
            if participante == usuario:
                continue
            if not usuario.matches.filter(pk=participante.pk).exists():
                raise PermissionDenied("Solo puedes chatear con usuarios con los que tienes match.")

        nueva_conversacion = serializer.save()
        nueva_conversacion.participantes.add(usuario, *participantes_qs)
        nueva_conversacion.save(update_fields=["fecha_actualizacion"])

    # Listar mensajes
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

    # Enviar mensaje
    @action(detail=True, methods=["post"], url_path="enviar")
    def enviar(self, request, pk=None):
        conversacion_obj = self.get_object()
        contenido = request.data.get("contenido", "").strip()

        if not contenido:
            return Response(
                {"detail": "El contenido del mensaje es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not conversacion_obj.participantes.filter(pk=request.user.pk).exists():
            return Response({"detail": "No participas en esta conversación."}, status=status.HTTP_403_FORBIDDEN)

        otros_participantes = conversacion_obj.participantes.exclude(pk=request.user.pk)
        faltan_matches = otros_participantes.exclude(pk__in=request.user.matches.values_list("pk", flat=True))
        if faltan_matches.exists():
            return Response({"detail": "Solo puedes chatear con usuarios con los que tienes match."},
                            status=status.HTTP_403_FORBIDDEN)

        nuevo_mensaje = mensaje.objects.create(
            conversacion=conversacion_obj,
            remitente=request.user,
            contenido=contenido,
        )

        conversacion_obj.fecha_actualizacion = timezone.now()
        conversacion_obj.save(update_fields=["fecha_actualizacion"])

        serializer = self.get_serializer(nuevo_mensaje)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ============================
# ASGI-SAFE SSE ENDPOINT
# ============================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([EventStreamRenderer])
async def mensajes_sse(request, pk):
    """
    SSE async endpoint that works correctly on ASGI (uvicorn).
    No blocking, no sync generators, no time.sleep(), no worker crashes.
    """

    # Get conversation asynchronously
    try:
        conversacion_obj = await sync_to_async(
            conversacion.objects.prefetch_related("participantes").get
        )(pk=pk)
    except conversacion.DoesNotExist:
        raise Http404("Conversación no encontrada")

    # Validate participation
    es_participante = await sync_to_async(
        conversacion_obj.participantes.filter(pk=request.user.pk).exists
    )()
    if not es_participante:
        return HttpResponseForbidden("No participas en esta conversación.")

    # Validate match rules
    otros_participantes = await sync_to_async(list)(
        conversacion_obj.participantes.exclude(pk=request.user.pk)
    )
    for participante in otros_participantes:
        tiene_match = await sync_to_async(
            request.user.matches.filter(pk=participante.pk).exists
        )()
        if not tiene_match:
            return HttpResponseForbidden("Solo puedes chatear con usuarios con los que tienes match.")

    # Initialize last_id
    try:
        last_id = int(request.query_params.get("last_id", "0"))
    except ValueError:
        last_id = 0

    # ============================
    # ASGI-compatible async generator
    # ============================
    async def event_stream():
        nonlocal last_id

        logger.debug("SSE stream opened for conversacion=%s user=%s", pk, request.user.pk)

        # First ping
        yield b": stream-start\n\n"

        while True:
            # Query new messages (async)
            nuevos = await sync_to_async(
                list
            )(mensaje.objects.filter(conversacion_id=pk, id__gt=last_id).order_by("id"))

            for msg in nuevos:
                last_id = msg.id
                payload = MensajeSerializer(msg).data
                logger.debug("SSE emit msg=%s in conversacion=%s to user=%s", msg.id, pk, request.user.pk)

                yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")

            # Heartbeat
            hb = f"event: ping\ndata: {int(asyncio.get_running_loop().time())}\n\n".encode("utf-8")
            yield hb

            # async sleep (never block!)
            await asyncio.sleep(2)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-transform"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"

    return response
