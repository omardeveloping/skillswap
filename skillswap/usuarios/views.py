from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, F
from .models import (
    Usuario,
    Habilidad,
    TipoHabilidad,
    ValoracionUsuario,
    SolicitudMatch,
    Notificacion,
)
from .serializers import (
    UsuarioSerializer,
    UsuarioCoincidenciaSerializer,
    HabilidadSerializer,
    TipoHabilidadSerializer,
    ValoracionUsuarioSerializer,
    SolicitudMatchSerializer,
    NotificacionSerializer,
)

# Create your views here.
class UsuarioViewset(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioSerializer

    def get_serializer_class(self):
        if self.action == "coincidencias":
            return UsuarioCoincidenciaSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def coincidencias(self, request):
        usuario = request.user
        habilidades_que_sabe = list(usuario.habilidades_que_se_saben.values_list("pk", flat=True))
        habilidades_por_aprender = list(usuario.habilidades_por_aprender.values_list("pk", flat=True))

        if not habilidades_que_sabe and not habilidades_por_aprender:
            return Response([])

        usuarios_compatibles = (
            Usuario.objects.exclude(pk=usuario.pk)
            .annotate(
                puede_ensenar=Count(
                    "habilidades_que_se_saben",
                    filter=Q(habilidades_que_se_saben__in=habilidades_por_aprender),
                    distinct=True,
                ),
                puede_aprender=Count(
                    "habilidades_por_aprender",
                    filter=Q(habilidades_por_aprender__in=habilidades_que_sabe),
                    distinct=True,
                ),
            )
            .filter(Q(puede_ensenar__gt=0) | Q(puede_aprender__gt=0))
            .annotate(total_coincidencias=F("puede_ensenar") + F("puede_aprender"))
            .order_by("-total_coincidencias", "-puede_ensenar", "-puede_aprender", "nombre")
        )

        pagina = self.paginate_queryset(usuarios_compatibles)
        if pagina is not None:
            serializer = self.get_serializer(pagina, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(usuarios_compatibles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="buscar")
    def buscar(self, request):
        termino = request.query_params.get("q", "").strip()

        if not termino:
            return Response({"detail": "Proporciona un término de búsqueda en 'q'."}, status=400)

        usuarios_filtrados = (
            self.get_queryset()
            .filter(
                Q(nombre__icontains=termino)
                | Q(segundo_nombre__icontains=termino)
                | Q(apellido__icontains=termino)
                | Q(habilidades_que_se_saben__nombre_habilidad__icontains=termino)
                | Q(habilidades_por_aprender__nombre_habilidad__icontains=termino)
            )
            .distinct()
        )

        pagina = self.paginate_queryset(usuarios_filtrados)
        if pagina is not None:
            serializer = self.get_serializer(pagina, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(usuarios_filtrados, many=True)
        return Response(serializer.data)

class HabilidadViewset(viewsets.ModelViewSet):
    queryset = Habilidad.objects.all()
    serializer_class = HabilidadSerializer
    permission_classes = [IsAuthenticated]


class TipoHabilidadViewset(viewsets.ModelViewSet):
    queryset = TipoHabilidad.objects.all()
    serializer_class = TipoHabilidadSerializer
    permission_classes = [IsAuthenticated]


class ValoracionUsuarioViewset(viewsets.ModelViewSet):
    queryset = ValoracionUsuario.objects.select_related("evaluador", "evaluado")
    serializer_class = ValoracionUsuarioSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(evaluador=self.request.user)


class SolicitudMatchViewset(viewsets.ModelViewSet):
    serializer_class = SolicitudMatchSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return SolicitudMatch.objects.select_related("emisor", "recipiente").filter(Q(emisor=user) | Q(recipiente=user))

    def perform_create(self, serializer):
        serializer.save(emisor=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def aceptar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.recipiente != request.user:
            return Response({"detail": "Solo el destinatario puede aceptar la solicitud."}, status=status.HTTP_403_FORBIDDEN)

        solicitud.aceptar()
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        if solicitud.recipiente != request.user:
            return Response({"detail": "Solo el destinatario puede rechazar la solicitud."}, status=status.HTTP_403_FORBIDDEN)

        solicitud.rechazar()
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)


class NotificacionViewset(viewsets.ModelViewSet):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Notificacion.objects.select_related("contexto", "contexto__emisor", "contexto__recipiente").filter(usuario=self.request.user)
