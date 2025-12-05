from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConversacionViewSet, mensajes_sse

router = DefaultRouter()
router.register(r"conversaciones", ConversacionViewSet, basename="conversacion")

urlpatterns = [
    path("conversaciones/<int:pk>/stream/", mensajes_sse, name="conversacion-stream"),
] + router.urls
