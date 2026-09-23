"""GeoConnect messages: serializers."""

from rest_framework import serializers

from accounts.serializers import PublicUserSerializer

from .models import RoomMessage


class RoomMessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True)
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)

    class Meta:
        model = RoomMessage
        fields = ("id", "room_id", "sender", "sender_id", "content", "created_at")

    def validate_content(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Message content is required.")
        if len(value) > 2000:
            raise serializers.ValidationError("Message must be at most 2000 characters.")
        return value