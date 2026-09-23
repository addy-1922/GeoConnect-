"""GeoConnect notifications: serializers."""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.SerializerMethodField()
    room_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "message",
            "is_read",
            "created_at",
            "actor_username",
            "room_id",
            "room_name",
        )

    def get_actor_username(self, obj):
        return obj.actor.username if obj.actor else None

    def get_room_name(self, obj):
        return obj.room.name if obj.room else None