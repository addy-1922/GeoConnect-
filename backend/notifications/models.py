"""GeoConnect notifications: Notification model."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A notification delivered to a single user."""

    class Type(models.TextChoices):
        SYSTEM = "system", "System"
        MEMBER_ADDED = "member_added", "Member Added"
        USER_JOINED = "user_joined", "User Joined"
        USER_LEFT = "user_left", "User Left"
        ROOM_DELETED = "room_deleted", "Room Deleted"
        ROLE_CHANGED = "role_changed", "Role Changed"
        EVENT_CREATED = "event_created", "Event Created"
        MARKER_CREATED = "marker_created", "Marker Created"
        LOCATION_SHARED = "location_shared", "Location Shared"
        LOCATION_STOPPED = "location_stopped", "Location Stopped"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acted_notifications",
    )
    type = models.CharField(max_length=24, choices=Type.choices, default=Type.SYSTEM)
    message = models.CharField(max_length=255)
    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"Notification({self.user_id}, {self.type})"