"""GeoConnect events: business logic (create + real-time relay)."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from notifications import services as notification_services
from notifications.models import Notification

from .models import LocationEvent
from .serializers import LocationEventSerializer


def create_event(room, created_by, title, description="", latitude=0.0, longitude=0.0, start_time=None):
    """Persist an event, notify the room, and relay it over the WebSocket."""
    event = LocationEvent.objects.create(
        room=room,
        created_by=created_by,
        title=title,
        description=description or "",
        latitude=latitude,
        longitude=longitude,
        start_time=start_time,
    )

    payload = {"type": "event_created", "event": LocationEventSerializer(event).data}
    try:
        async_to_sync(get_channel_layer().group_send)(f"room_{room.id}", payload)
    except Exception:
        pass

    for membership in room.memberships.select_related("user").exclude(user=created_by):
        notification_services.create_notification(
            membership.user,
            f"New event '{event.title}' in '{room.name}'",
            Notification.Type.EVENT_CREATED,
            actor=created_by,
            room=room,
        )
    return event