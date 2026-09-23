"""GeoConnect messages: RoomMessage model (persisted chat entries)."""

from django.conf import settings
from django.db import models


class RoomMessage(models.Model):
    """A chat message inside a room. Persisted in PostgreSQL and relayed by WS."""

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_messages",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["room", "-id"]),
        ]

    def __str__(self):
        return f"#{self.room_id} {self.sender_id}: {self.content[:40]}"