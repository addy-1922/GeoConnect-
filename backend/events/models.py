"""GeoConnect events: LocationEvent model (a scheduled meet-up at coordinates)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_latitude(value):
    if not (-90 <= value <= 90):
        raise ValidationError("Latitude must be between -90 and 90.")


def validate_longitude(value):
    if not (-180 <= value <= 180):
        raise ValidationError("Longitude must be between -180 and 180.")


class LocationEvent(models.Model):
    """An event pinned to a location inside a room (e.g. 'meet at the metro')."""

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="events",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_events",
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    latitude = models.FloatField(validators=[validate_latitude])
    longitude = models.FloatField(validators=[validate_longitude])
    start_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["room"])]

    def __str__(self):
        return f"{self.title} @ {self.room_id}"