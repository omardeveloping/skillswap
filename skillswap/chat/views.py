import json
import logging
import asyncio

from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.authtoken.models import Token
from asgiref.sync import sync_to_async

from usuarios.models import Usuario
from .models import conversacion, mensaje
from .serializers import ConversacionSerializer, MensajeSerializer

logger = logging.getLogger(__name__)


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
            raise ValidationError({"participantes": "Debes incluir al menos un participante."})

        participantes_qs = Usuario.objects.filter(pk__in=participantes_ids)
        if participantes_qs.count() != len(participantes_ids):
            raise ValidationError({"participantes": "Uno o más participantes no existen."})

        usuario = self.request.user

        for participante in participantes_qs:
            if participante != usuario and not usuario.matches.filter(pk=participante.pk).exists():
                raise PermissionDenied("Solo puedes chatear con usuarios con los que tienes match.")

        nueva = serializer.save()
        nueva.participantes.add(usuario, *participantes_qs)
        nueva.save(update_fields=["fecha_actualizacion"])

    @action(detail=True, methods=["get"], url_path="mensajes")
    def mensajes(self, request, pk=None):
        conv = self.get_object()
        mensajes_qs = conv.mensajes.select_related("remitente").order_by("enviado_en", "id")

        since = request.query_params.get("since")
        if since:
            parsed = parse_datetime(since)
            if parsed is None:
                return Response({"detail": "Parámetro 'since' inválido."},
                                status=status.HTTP_400_BAD_REQUEST)
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
            mensajes_qs = mensajes_qs.filter(enviado_en__gt=parsed)

        return Response(MensajeSerializer(mensajes_qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="enviar")
    def enviar(self, request, pk=None):
        conv = self.get_object()
        contenido = request.data.get("contenido", "").strip()

        if not contenido:
            return Response({"detail": "Contenido obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not conv.participantes.filter(pk=request.user.pk).exists():
            return Response({"detail": "No participas en esta conversación."},
                            status=status.HTTP_403_FORBIDDEN)

        otros = conv.participantes.exclude(pk=request.user.pk)
        sin_match = otros.exclude(pk__in=request.user.matches.values_list("pk", flat=True))

        if sin_match.exists():
            return Response({"detail": "Solo puedes chatear con usuarios con los que tienes match."},
                            status=status.HTTP_403_FORBIDDEN)

        nuevo = mensaje.objects.create(
            conversacion=conv, remitente=request.user, contenido=contenido
        )

        conv.fecha_actualizacion = timezone.now()
        conv.save(update_fields=["fecha_actualizacion"])

        return Response(MensajeSerializer(nuevo).data, status=status.HTTP_201_CREATED)


async def mensajes_sse(request, pk):
    """
    SSE streaming endpoint.
    DRF-free. Manual token authentication.
    Compatible with Uvicorn and Nginx.
    """

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Token "):
        return HttpResponseForbidden("Token missing")

    token_key = auth.split(" ", 1)[1]

    try:
        token = await sync_to_async(Token.objects.get)(key=token_key)
    except Token.DoesNotExist:
        return HttpResponseForbidden("Invalid token")

    user = await sync_to_async(lambda: token.user)()


    try:
        conv = await sync_to_async(
            conversacion.objects.prefetch_related("participantes").get
        )(pk=pk)
    except conversacion.DoesNotExist:
        raise Http404("Conversación no encontrada")

    is_participant = await sync_to_async(
        conv.participantes.filter(pk=user.pk).exists
    )()
    if not is_participant:
        return HttpResponseForbidden("No participas en esta conversación.")

    otros = await sync_to_async(list)(conv.participantes.exclude(pk=user.pk))
    for p in otros:
        has_match = await sync_to_async(
            user.matches.filter(pk=p.pk).exists
        )()
        if not has_match:
            return HttpResponseForbidden("Solo chateas con usuarios con match.")

    try:
        last_id = int(request.GET.get("last_id", 0))
    except:
        last_id = 0

    async def stream():
        nonlocal last_id
        yield b": stream-start\n\n"

        while True:
            nuevos = await sync_to_async(list)(
                mensaje.objects.filter(conversacion_id=pk, id__gt=last_id).order_by("id")
            )

            for msg in nuevos:
                last_id = msg.id
                data = MensajeSerializer(msg).data
                yield f"data: {json.dumps(data)}\n\n".encode()

            yield b"event: ping\ndata: keepalive\n\n"
            await asyncio.sleep(2)

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp
