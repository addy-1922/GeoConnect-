"""GeoConnect events: serializers."""

from rest_framework import serializers

from accounts.serializers import PublicUserSerializer

from .models import LocationEvent, validate_latitude, validate_longitude


class LocationEventSerializer(serializers.ModelSerializer):
    created_by = PublicUserSerializer(read_only=True)
    created_by_id = serializers.IntegerField(source="created_by.id", read_only=True)

    class Meta:
        model = LocationEvent
        fields = (
            "id",
            "room_id",
            "created_by",
            "created_by_id",
            "title",
            "description",
            "latitude",
            "longitude",
            "start_time",
            "created_at",
        )

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("An event title is required.")
        return value[:120]

    def validate_latitude(self, value):
        validate_latitude(value)
        return value

    def validate_longitude(self, value):
        validate_longitude(value)
        return value

    def validate_start_time(self, value):
        if value is None:
            return None
        from django.utils import timezone

        if value < timezone.now():
            raise serializers.ValidationError("Start time cannot be in the past.")
        return value