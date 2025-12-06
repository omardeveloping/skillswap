from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.db import transaction


class TipoHabilidad(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Habilidad(models.Model):
    nombre_habilidad = models.CharField(max_length=100)
    tipo = models.ForeignKey(TipoHabilidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="habilidades")

    def __str__(self):
        return self.nombre_habilidad


class UsuarioManager(BaseUserManager):
    use_in_migrations = True
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)
    
class ValoracionUsuarioChoices(models.IntegerChoices):
    MUY_MALO = 1, _("1")
    MALO = 2, _("2")
    REGULAR = 3, _("3")
    BUENO = 4, _("4")
    EXCELENTE = 5, _("5")

class ValoracionUsuario(models.Model):
    evaluador = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='valoraciones_realizadas')
    evaluado = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='valoraciones_recibidas')
    puntuacion = models.IntegerField(choices=ValoracionUsuarioChoices.choices, default=ValoracionUsuarioChoices.BUENO)
    comentario = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(evaluador=models.F('evaluado')), name='no_autovaloracion'),
            models.UniqueConstraint(fields=['evaluador', 'evaluado'], name='una_valoracion_por_usuario'),
        ]

    def __str__(self):
        return f'Valoracion {self.puntuacion} de {self.evaluador.email} a {self.evaluado.email}'

class Usuario(AbstractUser):
    username = None
    first_name = None
    last_name = None

    nombre = models.CharField(max_length=100)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100)
    year = models.IntegerField(blank=True, null=True)
    habilidades_que_se_saben = models.ManyToManyField(
        Habilidad,
        related_name="usuarios_que_saben",
        blank=True,
        verbose_name=_("habilidades que se saben"),
        help_text=_("Selecciona las habilidades que dominas."),
    )
    habilidades_por_aprender = models.ManyToManyField(
        Habilidad,
        related_name="usuarios_que_quieren_aprender",
        blank=True,
        verbose_name=_("habilidades que se quieren aprender"),
        help_text=_("Selecciona las habilidades que quieres aprender."),
    )
    email = models.EmailField(_("email address"), unique=True)
    telefono = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        validators=[RegexValidator(r"^\+?\d{9,15}$", message=_("Ingresa un número de teléfono válido."))],
        help_text=_("Formato recomendado: +56912345678"),
    )
    media = models.ImageField(upload_to='media/', blank=True, null=True)
    valoraciones = models.ManyToManyField(
        'self',
        through='ValoracionUsuario',
        symmetrical=False,
        related_name='valorado_por',
        blank=True,
    )
    matches = models.ManyToManyField(
        "self",
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["nombre", "apellido"]

    objects = UsuarioManager()

    @property
    def whatsapp_link(self):
        if not self.telefono:
            return None
        numero = "".join(filter(str.isdigit, self.telefono))
        return f"https://wa.me/{numero}" if numero else None


class SolicitudMatchEstado(models.TextChoices):
    INDEFINIDO = "indefinido", _("Indefinido")
    ACEPTADO = "aceptado", _("Aceptado")
    RECHAZADO = "rechazado", _("Rechazado")


class SolicitudMatch(models.Model):
    emisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="solicitudes_enviadas")
    recipiente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="solicitudes_recibidas")
    estado = models.CharField(
        max_length=15,
        choices=SolicitudMatchEstado.choices,
        default=SolicitudMatchEstado.INDEFINIDO,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(emisor=models.F("recipiente")),
                name="solicitud_match_sin_autosolicitud",
            )
        ]

    def __str__(self):
        return f"Solicitud de {self.emisor.email} a {self.recipiente.email} - {self.estado}"

    def aceptar(self):
        if self.estado != SolicitudMatchEstado.INDEFINIDO:
            return
        with transaction.atomic():
            self.estado = SolicitudMatchEstado.ACEPTADO
            self.save(update_fields=["estado", "actualizado_en"])
            self.notificaciones.update(mostrar=False)
            self.emisor.matches.add(self.recipiente)

    def rechazar(self):
        if self.estado != SolicitudMatchEstado.INDEFINIDO:
            return
        with transaction.atomic():
            self.estado = SolicitudMatchEstado.RECHAZADO
            self.save(update_fields=["estado", "actualizado_en"])
            self.notificaciones.update(mostrar=False)


class NotificacionTipo(models.TextChoices):
    SOLICITUD_MATCH = "solicitud_match", _("Solicitud de match")


class Notificacion(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=50, choices=NotificacionTipo.choices)
    contexto = models.ForeignKey(SolicitudMatch, on_delete=models.CASCADE, related_name="notificaciones")
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="notificaciones")
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)
    mostrar = models.BooleanField(default=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.titulo} ({self.tipo})"
