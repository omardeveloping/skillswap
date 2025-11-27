from rest_framework.routers import DefaultRouter
from .views import UsuarioViewset, HabilidadViewset, TipoHabilidadViewset, ValoracionUsuarioViewset

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewset)
router.register(r'habilidades', HabilidadViewset)
router.register(r'tipos-habilidad', TipoHabilidadViewset)
router.register(r'valoraciones', ValoracionUsuarioViewset)

urlpatterns = router.urls
