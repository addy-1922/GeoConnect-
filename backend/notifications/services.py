"""GeoConnect notifications: business logic (create + real-time broadcast)."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


def _payload(notification):
    return {
        "type": "notification",
        "id": notification.id,
        "type_name": notification.type,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "actor_username": notification.actor.username if notification.actor else None,
        "room_id": notification.room_id,
        "room_name": notification.room.name if notification.room else None,
    }


def _broadcast(user_id, payload):
    try:
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(f"user_{user_id}", payload)
    except Exception:
        # Broadcasting is best-effort during development; never crash a request.
        pass


def create_notification(user, message, type=Notification.Type.SYSTEM, actor=None, room=None):
    """Persist a notification for `user` and push it over the WebSocket."""
    notification = Notification.objects.create(
        user=user,
        actor=actor,
        type=type,
        message=message,
        room=room,
    )
    _broadcast(user.id, _payload(notification))
    return notification


def notify_role_changed(user, room, new_role):
    return create_notification(
        user,
        f"Your role in '{room.name}' is now {new_role}.",
        Notification.Type.ROLE_CHANGED,
        room=room,
    )


def notify_room_updated(user, room):
    return create_notification(
        user,
        f"Room '{room.name}' was updated.",
        Notification.Type.SYSTEM,
        room=room,
    )


def notify_room_deleted(user, room_name):
    return create_notification(
        user,
        f"Room '{room_name}' was deleted.",
        Notification.Type.ROOM_DELETED,
    )