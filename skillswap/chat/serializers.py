from rest_framework import serializers
from .models import conversacion, mensaje

class ConversacionSerializer(serializers.ModelSerializer):
    participantes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = conversacion
        fields = "__all__"

class MensajeSerializer(serializers.ModelSerializer):
    remitente = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = mensaje
        fields = "__all__"