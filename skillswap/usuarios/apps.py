from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        # Importar señales para registrar los listeners al iniciar la app.
        import usuarios.signals  # noqa: F401
