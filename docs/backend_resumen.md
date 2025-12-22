# Resumen del backend de SkillSwap

Este documento resume la estructura y los flujos principales del backend de SkillSwap para que nuevos contribuidores puedan entender rápidamente cómo funciona la API.

## Pila tecnológica y configuración base
- **Framework**: Django 5.2.8 con Django REST Framework para exponer APIs.
- **Autenticación**: Tokens (DRF) y sesiones. Se usa `dj-rest-auth` + `django-allauth` para registro e inicio de sesión, con un modelo de usuario personalizado que usa el email como identificador.
- **Internacionalización**: Configuración regional `es-cl` y zona horaria `America/Santiago`.
- **CORS/CSRF**: Permite orígenes específicos (localhost:5173, dominios de producción) y habilita credenciales.
- **Archivos estáticos y media**: MEDIA_ROOT apunta a `media/` y se sirven en desarrollo con `DEBUG=True`.

## Apps y responsabilidades
- **core**: `healthcheck` simple en la raíz (`/`) para verificaciones de disponibilidad.
- **usuarios**: Gestión de personas, habilidades, coincidencias (match), valoraciones y notificaciones.
- **chat**: Conversaciones y mensajes entre usuarios que ya hicieron match, con streaming SSE.

## Modelos clave
- **Usuario** (`usuarios.models.Usuario`): Extiende `AbstractUser` eliminando username; campos de nombre, segundo nombre, apellido, email único, teléfono validado, imagen de perfil y enlaces de WhatsApp generados. Mantiene relaciones ManyToMany con habilidades que sabe y quiere aprender, además de matches entre usuarios.
- **Habilidad / TipoHabilidad**: Catálogo de habilidades agrupadas por tipo.
- **ValoracionUsuario**: Relaciona evaluador y evaluado, con puntuación de 1-5, comentario opcional y restricciones para evitar auto-valoraciones y duplicados.
- **SolicitudMatch**: Solicitudes de conexión entre usuarios con estados `indefinido`, `aceptado` o `rechazado`, controlando que no se envíen a uno mismo. Aceptar agrega el match y oculta notificaciones relacionadas.
- **Notificacion**: Guarda eventos (por ahora `solicitud_match`) con flags de lectura y visibilidad, ordenados del más reciente al más antiguo.
- **Conversacion** (chat): Agrupa participantes y actualiza `fecha_actualizacion` al enviar mensajes.
- **Mensaje** (chat): Contenido, remitente, marca de lectura y timestamp por conversación.

## Endpoints principales
- **Autenticación** (`/api/auth/` y `/api/auth/registration/`): Manejado por `dj-rest-auth`; usa serializadores personalizados para login/registro con email.
- **Usuarios** (`/api/usuarios/`): CRUD completo. Acciones adicionales:
  - `coincidencias/`: devuelve usuarios compatibles según habilidades que sabe/quiere aprender el solicitante, paginado.
  - `buscar/?q=...`: filtro por nombre/apellidos o nombres de habilidades.
- **Habilidades y tipos**: `/api/habilidades/` y `/api/tipos-habilidad/` con CRUD protegido.
- **Valoraciones**: `/api/valoraciones/` permite crear/consultar valoraciones; el evaluador se fija al usuario autenticado.
- **Solicitudes de match**: `/api/solicitudes-match/` (GET/POST/DELETE) y acciones `aceptar/` y `rechazar/` para el destinatario.
- **Notificaciones**: `/api/notificaciones/` listado filtrado por usuario actual y actualizaciones parciales (ej. marcar leído/mostrar).
- **Chat** (`/api/chat/conversaciones/`):
  - Listado/creación de conversaciones solo con participantes que ya tienen match.
  - `mensajes/`: lista mensajes, acepta filtro `?since=` en ISO para obtener solo los nuevos.
  - `enviar/`: crea mensajes dentro de una conversación donde el usuario participa y mantiene match.
  - `conversaciones/<id>/stream/`: endpoint SSE (autenticación por Token) que emite mensajes en tiempo real.
- **Healthcheck**: `/` responde `{ "status": "ok" }`.

## Flujos recomendados
1. Registrar usuario vía `/api/auth/registration/` y completar perfil (habilidades que sabe y desea aprender).
2. Buscar coincidencias o usuarios por nombre/habilidad; enviar `solicitudes-match` a quienes interesen.
3. Cuando el destinatario acepta, ambos quedan en `matches` y pueden abrir una conversación de chat.
4. Enviar y recibir mensajes; el cliente puede suscribirse por SSE para actualizaciones en vivo.
5. Tras colaborar, crear `valoraciones` para retroalimentación entre usuarios.

## Archivos de referencia
- Configuración y seguridad: `skillswap/skillswap/settings.py`.
- Modelos y serializers: app `usuarios` y `chat` (modelos, serializers y vistas en el mismo directorio).
- Rutas API: `skillswap/skillswap/urls.py`, `usuarios/urls.py`, `chat/urls.py`, `core/urls.py`.

## Generación del PDF
Ejecuta `python docs/generar_pdf_resumen.py` para producir `docs/backend_resumen.pdf` a partir de este resumen (no necesita dependencias externas).
