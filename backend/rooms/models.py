"""GeoConnect rooms: Room and RoomMember models, with OWNER/ADMIN/MEMBER roles."""

from django.conf import settings
from django.db import models


class Room(models.Model):
    """A location-based collaboration room."""

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_private = models.BooleanField(
        default=False,
        help_text="Private rooms can only be accessed by invited members.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="owned_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.memberships.count()


class RoomMember(models.Model):
    """Membership of a user in a room, with a role."""

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["room", "user"], name="unique_room_member"),
        ]
        indexes = [
            models.Index(fields=["room", "user"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.room.name} ({self.role})"