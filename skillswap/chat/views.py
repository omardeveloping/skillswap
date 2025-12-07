import json
import logging
import asyncio

from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.utils import timezone
from asgiref.sync import sync_to_async

from rest_framework.authtoken.models import Token

from .models import conversacion, mensaje
from .serializers import MensajeSerializer

logger = logging.getLogger(__name__)


async def mensajes_sse(request, pk):
    """
    Fully ASGI-compatible, DRF-free SSE endpoint.
    """

    # -------------------------------
    # 1. MANUAL TOKEN AUTHENTICATION
    # -------------------------------
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Token "):
        return HttpResponseForbidden("Token missing")

    token_key = auth.split(" ", 1)[1]

    try:
        token = await sync_to_async(Token.objects.get)(key=token_key)
    except Token.DoesNotExist:
        return HttpResponseForbidden("Invalid token")

    user = token.user
    request.user = user

    # -------------------------------
    # 2. GET CONVERSATION
    # -------------------------------
    try:
        conv = await sync_to_async(
            conversacion.objects.prefetch_related("participantes").get
        )(pk=pk)
    except conversacion.DoesNotExist:
        raise Http404("Conversación no encontrada")

    # Must be participant
    is_participant = await sync_to_async(
        conv.participantes.filter(pk=user.pk).exists
    )()
    if not is_participant:
        return HttpResponseForbidden("No participas en esta conversación.")

    # Validate matches
    otros = await sync_to_async(list)(conv.participantes.exclude(pk=user.pk))
    for p in otros:
        has_match = await sync_to_async(
            user.matches.filter(pk=p.pk).exists
        )()
        if not has_match:
            return HttpResponseForbidden("Solo puedes chatear con usuarios con los que tienes match.")

    # -------------------------------
    # 3. last_id
    # -------------------------------
    try:
        last_id = int(request.GET.get("last_id", 0))
    except:
        last_id = 0

    # -------------------------------
    # 4. ASYNC SSE GENERATOR
    # -------------------------------
    async def event_stream():
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

            # heartbeat every 2 seconds
            yield b"event: ping\ndata: keepalive\n\n"

            await asyncio.sleep(2)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response
