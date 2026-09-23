"""GeoConnect: built-in User extended with a UserProfile (accounts app)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class Profile(models.Model):
    """Extra profile data attached to the built-in auth User (OneToOne)."""

    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        AWAY = "away", "Away"
        OFFLINE = "offline", "Offline"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OFFLINE,
    )
    is_sharing_location = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        return f"Profile({self.user.username})"


@receiver(post_save, sender=User)
def create_profile_on_user_create(sender, instance, created, **kwargs):
    """Automatically create a Profile whenever a User is created."""
    if created:
        Profile.objects.create(user=instance)