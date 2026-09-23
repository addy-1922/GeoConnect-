"""GeoConnect accounts: business logic kept out of the views."""

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Profile

User = get_user_model()


def register_user(username, email, password):
    """Create an active user + profile. Returns the user."""
    user = User.objects.create_user(username=username, email=email, password=password)
    user.profile.last_seen = timezone.now()
    user.profile.save(update_fields=["last_seen"])
    return user


def mark_seen(user):
    """Update the user's last_seen timestamp (used on key actions/WS connect)."""
    if not user or not user.is_authenticated:
        return
    profile = getattr(user, "profile", None)
    if profile is None:
        return
    profile.last_seen = timezone.now()
    profile.save(update_fields=["last_seen"])


def set_status(user, status):
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    from .models import Profile

    if status not in Profile.Status.values:
        return None
    profile.status = status
    profile.save(update_fields=["status"])
    return profile


def get_profile_or_none(user):
    return getattr(user, "profile", None)