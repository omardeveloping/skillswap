from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import Usuario, Carrera
from .serializers import UsuarioSerializer, CarreraSerializer

# Create your views here.
class UsuarioViewset(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]

class CarreraViewset(viewsets.ModelViewSet):
    queryset = Carrera.objects.all()
    serializer_class = CarreraSerializer
    permission_classes = [IsAuthenticated]
