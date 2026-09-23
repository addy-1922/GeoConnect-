"""GeoConnect locations: UserLocation (last-known) and MapMarker models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_latitude(value):
    if not (-90 <= value <= 90):
        raise ValidationError("Latitude must be between -90 and 90.")


def validate_longitude(value):
    if not (-180 <= value <= 180):
        raise ValidationError("Longitude must be between -180 and 180.")


class UserLocation(models.Model):
    """A user's last known location.

    Privacy: only the *latest* coordinate is stored (never a location history).
    It is only ever exposed to authorized members of rooms the user is in, and
    only while the user's location sharing is enabled.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_location",
    )
    latitude = models.FloatField(validators=[validate_latitude])
    longitude = models.FloatField(validators=[validate_longitude])
    accuracy = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserLocation({self.user_id})"

    def to_dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "updated_at": self.updated_at.isoformat(),
        }


class MapMarker(models.Model):
    """A user-created marker on the room map."""

    class MarkerType(models.TextChoices):
        MEETING_POINT = "meeting_point", "Meeting Point"
        DANGER = "danger", "Danger"
        FOOD = "food", "Food"
        PARKING = "parking", "Parking"
        IMPORTANT = "important", "Important"
        CUSTOM = "custom", "Custom"

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="markers",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="map_markers",
    )
    title = models.CharField(max_length=120)
    marker_type = models.CharField(
        max_length=20,
        choices=MarkerType.choices,
        default=MarkerType.CUSTOM,
    )
    latitude = models.FloatField(validators=[validate_latitude])
    longitude = models.FloatField(validators=[validate_longitude])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["room"])]

    def __str__(self):
        return f"{self.marker_type}: {self.title}"