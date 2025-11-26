from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import Usuario, Habilidad, TipoHabilidad
from .serializers import UsuarioSerializer, HabilidadSerializer, TipoHabilidadSerializer

# Create your views here.
class UsuarioViewset(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]

class HabilidadViewset(viewsets.ModelViewSet):
    queryset = Habilidad.objects.all()
    serializer_class = HabilidadSerializer
    permission_classes = [IsAuthenticated]


class TipoHabilidadViewset(viewsets.ModelViewSet):
    queryset = TipoHabilidad.objects.all()
    serializer_class = TipoHabilidadSerializer
    permission_classes = [IsAuthenticated]
