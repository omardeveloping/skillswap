from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Usuario, Habilidad, TipoHabilidad, ValoracionUsuario
from .serializers import UsuarioSerializer, HabilidadSerializer, TipoHabilidadSerializer, ValoracionUsuarioSerializer

# Create your views here.
class UsuarioViewset(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def coincidencias(self, request):
        usuario = request.user
        habilidades_usuario = list(usuario.habilidades.values_list("pk", flat=True))

        if not habilidades_usuario:
            return Response([])

        usuarios_compatibles = (
            Usuario.objects.exclude(pk=usuario.pk)
            .filter(habilidades__in=habilidades_usuario)
            .annotate(habilidades_compartidas=Count("habilidades", distinct=True))
            .order_by("-habilidades_compartidas", "nombre")
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
                | Q(habilidades__nombre_habilidad__icontains=termino)
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
