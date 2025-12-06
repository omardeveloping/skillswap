from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .models import (
    Usuario,
    Habilidad,
    TipoHabilidad,
    ValoracionUsuario,
    SolicitudMatch,
    SolicitudMatchEstado,
    Notificacion,
)

from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from dj_rest_auth.serializers import LoginSerializer

class UsuarioSerializer(serializers.ModelSerializer):
    whatsapp_link = serializers.SerializerMethodField(read_only=True)
    valorado_por = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = "__all__"

    def get_whatsapp_link(self, obj):
        return obj.whatsapp_link

class HabilidadSerializer(serializers.ModelSerializer):
    tipo = serializers.PrimaryKeyRelatedField(queryset=TipoHabilidad.objects.all())
    nombre_tipo = serializers.CharField(source='tipo.nombre', read_only=True)

    class Meta:
        model = Habilidad
        fields = "__all__"


class TipoHabilidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoHabilidad
        fields = "__all__"

class ValoracionUsuarioSerializer(serializers.ModelSerializer):
    evaluador = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ValoracionUsuario
        fields = "__all__"
        read_only_fields = ("evaluador",)

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["evaluador"] = request.user
        return super().create(validated_data)

    def validate(self, attrs):
        evaluador = self.context["request"].user if "request" in self.context else None
        evaluado = attrs.get("evaluado") or getattr(self.instance, "evaluado", None)
        if evaluador and evaluado and evaluador == evaluado:
            raise serializers.ValidationError(_("No puedes valorarte a ti mismo."))
        return super().validate(attrs)


class SolicitudMatchSerializer(serializers.ModelSerializer):
    emisor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SolicitudMatch
        fields = "__all__"
        read_only_fields = ("emisor", "estado", "creado_en", "actualizado_en")

    def validate(self, attrs):
        request = self.context.get("request")
        recipiente = attrs.get("recipiente") or getattr(self.instance, "recipiente", None)
        if request and request.user and recipiente:
            if request.user == recipiente:
                raise serializers.ValidationError(_("No puedes enviarte una solicitud a ti mismo."))
            if request.user.matches.filter(pk=recipiente.pk).exists():
                raise serializers.ValidationError(_("Ya tienes un match con este usuario."))

            existe_pendiente = SolicitudMatch.objects.filter(
                emisor=request.user,
                recipiente=recipiente,
                estado=SolicitudMatchEstado.INDEFINIDO,
            ).exists()
            if existe_pendiente:
                raise serializers.ValidationError(_("Ya enviaste una solicitud pendiente a este usuario."))

            pendiente_contra = SolicitudMatch.objects.filter(
                emisor=recipiente,
                recipiente=request.user,
                estado=SolicitudMatchEstado.INDEFINIDO,
            ).exists()
            if pendiente_contra:
                raise serializers.ValidationError(_("Tienes una solicitud pendiente de este usuario; respóndela allí."))
        return super().validate(attrs)


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = "__all__"
        read_only_fields = (
            "titulo",
            'descripcion',
            "tipo",
            "contexto",
            "usuario",
            "fecha",
        )


class CustomRegisterSerializer(RegisterSerializer):
    # Elimina el campo heredado "username" y usa email como identificador
    username = None
    email = serializers.EmailField(required=True)
    nombre = serializers.CharField()
    segundo_nombre = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    apellido = serializers.CharField()
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            "nombre": self.validated_data.get("nombre", ""),
            "segundo_nombre": self.validated_data.get("segundo_nombre", ""),
            "apellido": self.validated_data.get("apellido", ""),
            "telefono": self.validated_data.get("telefono", ""),
        })
        return data

    def save(self, request):
        user = super().save(request)
        user.nombre = self.cleaned_data.get("nombre", "")
        user.segundo_nombre = self.cleaned_data.get("segundo_nombre", "")
        user.apellido = self.cleaned_data.get("apellido", "")
        user.telefono = self.cleaned_data.get("telefono", "")
        user.save()
        return user

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
            "year",
            "media",
            "habilidades_que_se_saben",
            "habilidades_por_aprender",
            "telefono",
            "whatsapp_link",
        )
        extra_kwargs = {
            "email": {"read_only": True},  # no permitir editar email desde user endpoint
        }


class UsuarioCoincidenciaSerializer(UsuarioSerializer):
    puede_ensenar = serializers.SerializerMethodField()
    puede_aprender = serializers.SerializerMethodField()

    class Meta(UsuarioSerializer.Meta):
        # Keep base fields; declared SerializerMethodFields are added automatically.
        fields = UsuarioSerializer.Meta.fields

    def _get_request_user(self):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            return request.user
        return None

    def get_puede_ensenar(self, obj):
        user = self._get_request_user()
        if not user:
            return []
        habilidades_deseadas = user.habilidades_por_aprender.values_list("pk", flat=True)
        habilidades = obj.habilidades_que_se_saben.filter(pk__in=habilidades_deseadas)
        return HabilidadSerializer(habilidades, many=True).data

    def get_puede_aprender(self, obj):
        user = self._get_request_user()
        if not user:
            return []
        habilidades_que_puedo_ensenar = user.habilidades_que_se_saben.values_list("pk", flat=True)
        habilidades = obj.habilidades_por_aprender.filter(pk__in=habilidades_que_puedo_ensenar)
        return HabilidadSerializer(habilidades, many=True).data
