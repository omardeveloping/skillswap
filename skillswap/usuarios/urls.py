from rest_framework.routers import DefaultRouter
from .views import UsuarioViewset, HabilidadViewset, TipoHabilidadViewset

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewset)
router.register(r'habilidades', HabilidadViewset)
router.register(r'tipos-habilidad', TipoHabilidadViewset)

urlpatterns = router.urls
