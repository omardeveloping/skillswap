from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewset, CarreraViewset

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewset)
router.register(r'carreras', CarreraViewset)

urlpatterns = router.urls
