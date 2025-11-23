from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .models import Usuario, Carrera

from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from dj_rest_auth.serializers import LoginSerializer

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = "__all__"

class CarreraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrera
        fields = "__all__"

class CustomRegisterSerializer(RegisterSerializer):
    # Elimina el campo heredado "username" y usa email como identificador
    username = None
    email = serializers.EmailField(required=True)
    nombre = serializers.CharField()
    segundo_nombre = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    apellido = serializers.CharField()

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            "nombre": self.validated_data.get("nombre", ""),
            "segundo_nombre": self.validated_data.get("segundo_nombre", ""),
            "apellido": self.validated_data.get("apellido", ""),
        })
        return data

class CustomLoginSerializer(LoginSerializer):
    # Fuerza login por email; oculta username en el schema/UI
    username = None
    email = serializers.EmailField(required=True, allow_blank=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        user = self.get_auth_user(username=None, email=email, password=password)
        if not user:
            raise serializers.ValidationError(_("No se puede iniciar sesión con estas credenciales."))
        self.validate_auth_user_status(user)
        if "dj_rest_auth.registration" in settings.INSTALLED_APPS:
            self.validate_email_verification_status(user, email=email)
        attrs["user"] = user
        return attrs

class CustomUserDetailsSerializer(UserDetailsSerializer):
    class Meta(UserDetailsSerializer.Meta):
        model = Usuario
        fields = (
            "id",
            "email",
            "nombre",
            "segundo_nombre",
            "apellido",
            "carrera",
            "year",
            "media",
        )
        extra_kwargs = {
            "email": {"read_only": True},  # no permitir editar email desde user endpoint
        }
