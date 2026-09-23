"""GeoConnect messages: business logic (persist + real-time relay)."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import RoomMessage


def create_message(room, sender, content):
    """Persist a message and relay it to every socket in the room group."""
    content = (content or "").strip()
    if not content or len(content) > 2000:
        raise ValueError("Invalid message content.")

    message = RoomMessage.objects.create(room=room, sender=sender, content=content)

    from .serializers import RoomMessageSerializer

    payload = {"type": "chat_message", "message": RoomMessageSerializer(message).data}
    try:
        async_to_sync(get_channel_layer().group_send)(f"room_{room.id}", payload)
    except Exception:
        pass
    return message