"""GeoConnect locations: business logic (share/stop/update locations & markers)."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from accounts.models import Profile
from notifications import services as notification_services
from notifications.models import Notification

from .models import MapMarker, UserLocation


def update_user_location(user, latitude, longitude, accuracy=None):
    """Upsert the last-known location and enable sharing.

    Returns (location, sharing_just_enabled).
    """
    was_off = not user.profile.is_sharing_location

    location, _ = UserLocation.objects.update_or_create(
        user=user,
        defaults={
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
        },
    )

    if was_off:
        Profile.objects.filter(pk=user.profile.pk).update(is_sharing_location=True)
        user.profile.refresh_from_db()

    return location, was_off


def set_location_sharing(user, on):
    """Toggle location sharing ON/OFF. Keeps the last-known coordinate stored."""
    from accounts import services as account_services

    account_services.set_status(user, Profile.Status.ONLINE if on else Profile.Status.OFFLINE)
    profile = user.profile
    profile.is_sharing_location = bool(on)
    profile.save(update_fields=["is_sharing_location"])
    return profile


def notify_members(room, actor, message, type_):
    """Notify every member except the actor about a sharing state change."""
    for membership in room.memberships.select_related("user").exclude(user=actor):
        notification_services.create_notification(
            membership.user,
            message,
            type_,
            actor=actor,
            room=room,
        )


def create_marker(room, created_by, title, marker_type, latitude, longitude):
    """Create a marker and broadcast it to the room group."""
    marker = MapMarker.objects.create(
        room=room,
        created_by=created_by,
        title=title,
        marker_type=marker_type,
        latitude=latitude,
        longitude=longitude,
    )
    broadcast_room(room.id, "marker_created", {"marker": marker_payload(marker)})
    return marker


def broadcast_room(room_id, message_type, extra=None):
    payload = {"type": message_type}
    if extra:
        payload.update(extra)
    try:
        async_to_sync(get_channel_layer().group_send)(f"room_{room_id}", payload)
    except Exception:
        pass


def marker_payload(marker):
    from .serializers import MapMarkerSerializer

    return MapMarkerSerializer(marker).data