"""GeoConnect locations: WebSocket consumer for live location sharing.

Endpoint: /ws/location/<room_id>/

Lifecycle:
    connect        -> authorized member (session auth) joins the room group
    location_update -> upsert last-known location; if sharing was switched on
                       as a side effect, notify the room; then broadcast the
                       fresh coordinate to every socket in the room group
    stop_sharing   -> disable sharing (last-known coordinate stays on disk)
                      and broadcast the stop to the room group

Privacy: a coordinate is broadcast to the room group ONLY while the sender's
sharing flag is on, and only to members connected to THAT room.
"""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from notifications import services as notification_services
from notifications.models import Notification

from . import services
from .serializers import LocationPacketSerializer


class LocationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        # Dedicated group so room-hub frames (presence, chat, markers) never
        # get misrouted to this consumer, and vice-versa.
        self.room_group = f"location_room_{self.room_id}"

        if not await self._is_member(user.id, self.room_id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        room_group = getattr(self, "room_group", None)
        if room_group:
            # Last-known location + sharing flag stay persisted; the consumer
            # simply stops relaying updates for this client.
            await self.channel_layer.group_discard(room_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        if msg_type == "location_update":
            await self._handle_update(content)
        elif msg_type == "stop_sharing":
            await self._handle_stop_sharing()
        else:
            await self.send_json(
                {"type": "error", "message": f"Unknown message type: {msg_type}"}
            )

    async def _handle_update(self, content):
        packet = LocationPacketSerializer(data=content)
        if not packet.is_valid():
            await self.send_json(
                {
                    "type": "error",
                    "message": "; ".join(
                        f"{field}: {', '.join(errors)}"
                        for field, errors in packet.errors.items()
                    ),
                }
            )
            return

        data = packet.validated_data
        location, sharing_just_enabled = await database_sync_to_async(
            services.update_user_location
        )(
            self.user,
            data["latitude"],
            data["longitude"],
            data.get("accuracy"),
        )

        payload = {
            "user": await self._public_user(self.user.id),
            **location.to_dict(),
        }
        await self.channel_layer.group_send(
            self.room_group,
            {"type": "location_update", **payload},
        )

        if sharing_just_enabled:
            await self._notify_others(
                f"{self.user.username} started sharing their location",
                Notification.Type.LOCATION_SHARED,
            )
            await self.channel_layer.group_send(
                self.room_group,
                {"type": "location_shared", **payload},
            )

    async def _handle_stop_sharing(self):
        await database_sync_to_async(services.set_location_sharing)(self.user, False)
        await self._notify_others(
            f"{self.user.username} stopped sharing their location",
            Notification.Type.LOCATION_STOPPED,
        )
        await self.channel_layer.group_send(
            self.room_group,
            {"type": "location_stopped", "user": await self._public_user(self.user.id)},
        )

    async def _notify_others(self, message, type_):
        def _create_for_others():
            from rooms.models import Room, RoomMember

            room = Room.objects.get(pk=self.room_id)
            members = RoomMember.objects.filter(room_id=self.room_id).exclude(user_id=self.user.id)
            for membership in members.select_related("user"):
                notification_services.create_notification(
                    membership.user,
                    message,
                    type_,
                    actor=self.user,
                    room=room,
                )

        await database_sync_to_async(_create_for_others)()

    # ------------------------------------------------------------------
    # Group event handlers
    # ------------------------------------------------------------------
    async def location_update(self, event):
        await self.send_json({"type": "location_update", **event})

    async def location_shared(self, event):
        await self.send_json({"type": "location_shared", **event})

    async def location_stopped(self, event):
        await self.send_json({"type": "location_stopped", **event})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    @database_sync_to_async
    def _is_member(user_id, room_id):
        from rooms.models import RoomMember

        return RoomMember.objects.filter(room_id=room_id, user_id=user_id).exists()

    @staticmethod
    @database_sync_to_async
    def _public_user(user_id):
        from django.contrib.auth import get_user_model

        from accounts.serializers import PublicUserSerializer

        return PublicUserSerializer(get_user_model().objects.get(pk=user_id)).data