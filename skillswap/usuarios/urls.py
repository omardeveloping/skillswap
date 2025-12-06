from rest_framework.routers import DefaultRouter
from .views import (
    UsuarioViewset,
    HabilidadViewset,
    TipoHabilidadViewset,
    ValoracionUsuarioViewset,
    SolicitudMatchViewset,
    NotificacionViewset,
)

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewset)
router.register(r'habilidades', HabilidadViewset)
router.register(r'tipos-habilidad', TipoHabilidadViewset)
router.register(r'valoraciones', ValoracionUsuarioViewset)
router.register(r"solicitudes-match", SolicitudMatchViewset, basename="solicitud-match")
router.register(r"notificaciones", NotificacionViewset, basename="notificacion")

urlpatterns = router.urls
