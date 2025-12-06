from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from .models import Usuario, SolicitudMatch, Notificacion


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            "email",
            "nombre",
            "segundo_nombre",
            "apellido",
            "year",
            "media",
            "habilidades_que_se_saben",
            "habilidades_por_aprender",
        )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = (
            "email",
            "nombre",
            "segundo_nombre",
            "apellido",
            "year",
            "media",
            "habilidades_que_se_saben",
            "habilidades_por_aprender",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = Usuario
    list_display = ("email", "nombre", "apellido", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    ordering = ("email",)
    search_fields = ("email", "nombre", "apellido")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("nombre", "segundo_nombre", "apellido", "year", "media")}),
        (_("Habilidades"), {"fields": ("habilidades_que_se_saben", "habilidades_por_aprender")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "nombre",
                    "segundo_nombre",
                    "apellido",
                    "year",
                    "media",
                    "habilidades_que_se_saben",
                    "habilidades_por_aprender",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions", "habilidades_que_se_saben", "habilidades_por_aprender")


@admin.register(SolicitudMatch)
class SolicitudMatchAdmin(admin.ModelAdmin):
    list_display = ("emisor", "recipiente", "estado", "creado_en")
    list_filter = ("estado",)
    search_fields = ("emisor__email", "recipiente__email")


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "tipo", "mostrar", "leido", "fecha")
    list_filter = ("tipo", "mostrar", "leido")
    search_fields = ("titulo", "usuario__email")
