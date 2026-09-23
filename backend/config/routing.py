"""
WebSocket routing for Django Channels.

Endpoints:
    /ws/rooms/<room_id>/        room hub: chat, presence, events, markers
    /ws/location/<room_id>/     real-time location sharing for a room
    /ws/notifications/          per-user notification stream

URLRouter + AuthMiddlewareStack (see config/asgi.py) put the session-authenticated
user on `scope["user"]` so consumers can enforce membership checks.
"""

from django.urls import re_path
from channels.routing import URLRouter

from locations.consumers import LocationConsumer
from notifications.consumers import NotificationConsumer
from rooms.consumers import RoomConsumer

websocket_urlpatterns = [
    re_path(r"^ws/rooms/(?P<room_id>[0-9]+)/$", RoomConsumer.as_asgi()),
    re_path(r"^ws/location/(?P<room_id>[0-9]+)/$", LocationConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]

# Module-level ASGI application for the WebSocket protocol.
# Wrapped by the ProtocolTypeRouter in config/asgi.py, which adds
# AuthMiddlewareStack so the session cookie authenticates the socket.
application = URLRouter(websocket_urlpatterns)