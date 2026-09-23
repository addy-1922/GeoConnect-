"""GeoConnect locations: serializers."""

from rest_framework import serializers

from accounts.serializers import PublicUserSerializer

from .models import MapMarker, UserLocation, validate_latitude, validate_longitude


class UserLocationSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = UserLocation
        fields = ("user", "user_id", "latitude", "longitude", "accuracy", "updated_at")


class MapMarkerSerializer(serializers.ModelSerializer):
    created_by = PublicUserSerializer(read_only=True)
    created_by_id = serializers.IntegerField(source="created_by.id", read_only=True)
    marker_type = serializers.ChoiceField(choices=MapMarker.MarkerType.choices)

    class Meta:
        model = MapMarker
        fields = (
            "id",
            "room_id",
            "created_by",
            "created_by_id",
            "title",
            "marker_type",
            "latitude",
            "longitude",
            "created_at",
        )

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("A marker title is required.")
        return value[:120]

    def validate_latitude(self, value):
        validate_latitude(value)
        return value

    def validate_longitude(self, value):
        validate_longitude(value)
        return value


class LocationPacketSerializer(serializers.Serializer):
    """Validates coordinates arriving over the location WebSocket."""

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    accuracy = serializers.FloatField(required=False, allow_null=True, min_value=0)

    def validate_latitude(self, value):
        validate_latitude(value)
        return value

    def validate_longitude(self, value):
        validate_longitude(value)
        return value