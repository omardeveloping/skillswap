from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class TipoHabilidad(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Habilidad(models.Model):
    nombre_habilidad = models.CharField(max_length=100)
    tipo = models.ForeignKey(TipoHabilidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="habilidades")

    def __str__(self):
        return self.nombre

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

class Usuario(AbstractUser):
    username = None
    first_name = None
    last_name = None

    nombre = models.CharField(max_length=100)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100)
    year = models.IntegerField(blank=True, null=True)
    habilidades = models.ManyToManyField(Habilidad, related_name="usuarios", blank=True)
    email = models.EmailField(_("email address"), unique=True)
    media = models.ImageField(upload_to='media/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["nombre", "apellido"]

    objects = UsuarioManager()
