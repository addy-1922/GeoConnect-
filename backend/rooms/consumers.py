"""GeoConnect rooms: WebSocket consumer for chat, presence, events and markers.

Endpoint: /ws/rooms/<room_id>/
Events sent to the room group:
    room_snapshot   -> the connecting client (messages, participants, events,
                       markers, locations, online ids, my_role)
    user_joined     -> every client when a member connects
    user_left       -> every client when a member disconnects
    presence        -> every client with the updated online-id list
    chat_message    -> persisted + broadcast chat
    event_created   -> a new location event persisted + broadcast
    marker_created  -> a new map marker persisted + broadcast
"""

from asgiref.sync import sync_to_async

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from accounts.models import Profile
from locations.presence import mark_offline, mark_online, online_user_ids


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        self.room_group = f"room_{self.room_id}"

        if not await self._is_member(self.user.id, self.room_id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        await sync_to_async(mark_online)(self.room_id, self.user.id)
        await self._set_profile_status(self.user.id, Profile.Status.ONLINE)
        await self._mark_seen(self.user.id)

        online = sorted(await sync_to_async(online_user_ids)(self.room_id))
        await self.channel_layer.group_send(
            self.room_group,
            {"type": "presence", "online_ids": online},
        )
        await self.channel_layer.group_send(
            self.room_group,
            {"type": "user_joined", "user": await self._public_user(self.user.id)},
        )
        await self.send_json(await self._room_snapshot())

    async def disconnect(self, code):
        room_group = getattr(self, "room_group", None)
        if room_group:
            await self.channel_layer.group_discard(room_group, self.channel_name)
            await sync_to_async(mark_offline)(self.room_id, self.user.id)
            online = await sync_to_async(online_user_ids)(self.room_id)
            await self.channel_layer.group_send(
                room_group,
                {"type": "presence", "online_ids": sorted(online)},
            )
            await self.channel_layer.group_send(
                room_group,
                {"type": "user_left", "user": await self._public_user(self.user.id)},
            )
            await self._set_profile_status(self.user.id, Profile.Status.OFFLINE)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        if msg_type == "chat_message":
            await self._handle_chat(content)
        elif msg_type == "event_created":
            await self._handle_event(content)
        elif msg_type == "marker_created":
            await self._handle_marker(content)
        else:
            await self.send_json(
                {"type": "error", "message": f"Unknown message type: {msg_type}"}
            )

    # ------------------------------------------------------------------
    # Group event handlers (called by Channels when group messages arrive)
    # ------------------------------------------------------------------
    async def room_snapshot(self, event):
        await self.send_json(event)

    async def user_joined(self, event):
        await self.send_json({"type": "user_joined", "user": event["user"]})

    async def user_left(self, event):
        await self.send_json({"type": "user_left", "user": event["user"]})

    async def presence(self, event):
        await self.send_json({"type": "presence", "online_ids": event["online_ids"]})

    async def chat_message(self, event):
        await self.send_json({"type": "chat_message", "message": event["message"]})

    async def event_created(self, event):
        await self.send_json({"type": "event_created", "event": event["event"]})

    async def marker_created(self, event):
        await self.send_json({"type": "marker_created", "marker": event["marker"]})

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    async def _handle_chat(self, content):
        text = (content.get("content") or "").strip()
        if not text or len(text) > 2000:
            await self.send_json({"type": "error", "message": "Invalid message."})
            return
        from messages.models import RoomMessage
        from messages.serializers import RoomMessageSerializer

        message = await database_sync_to_async(RoomMessage.objects.create)(
            room_id=self.room_id,
            sender=self.user,
            content=text,
        )

        def _serialize():
            return RoomMessageSerializer(message).data

        await self.channel_layer.group_send(
            self.room_group,
            {"type": "chat_message", "message": await database_sync_to_async(_serialize)()},
        )

    async def _handle_event(self, content):
        from events.models import LocationEvent
        from events.serializers import LocationEventSerializer

        serializer = LocationEventSerializer(
            data=content,
            context={"request": self._fake_request()},
        )
        if not await database_sync_to_async(serializer.is_valid)(raise_exception=False):
            await self.send_json(
                {
                    "type": "error",
                    "message": "; ".join(
                        f"{field}: {', '.join(errors)}"
                        for field, errors in serializer.errors.items()
                    ),
                }
            )
            return
        event = await database_sync_to_async(serializer.save)(
            room_id=self.room_id,
            created_by=self.user,
        )
        await self._notify_event_created(event)

        def _serialize():
            return LocationEventSerializer(event).data

        await self.channel_layer.group_send(
            self.room_group,
            {"type": "event_created", "event": await database_sync_to_async(_serialize)()},
        )

    async def _handle_marker(self, content):
        from locations.models import MapMarker
        from locations.serializers import MapMarkerSerializer

        serializer = MapMarkerSerializer(
            data=content,
            context={"request": self._fake_request()},
        )
        if not await database_sync_to_async(serializer.is_valid)(raise_exception=False):
            await self.send_json(
                {
                    "type": "error",
                    "message": "; ".join(
                        f"{field}: {', '.join(errors)}"
                        for field, errors in serializer.errors.items()
                    ),
                }
            )
            return
        marker = await database_sync_to_async(serializer.save)(
            room_id=self.room_id,
            created_by=self.user,
        )

        def _serialize():
            return MapMarkerSerializer(marker).data

        await self.channel_layer.group_send(
            self.room_group,
            {"type": "marker_created", "marker": await database_sync_to_async(_serialize)()},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _room_snapshot(self):
        from .services import build_room_snapshot

        return await database_sync_to_async(build_room_snapshot)(self.user, self.room_id)

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

    @staticmethod
    @database_sync_to_async
    def _set_profile_status(user_id, status):
        from accounts.services import set_status
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(pk=user_id)
        return set_status(user, status)

    @staticmethod
    @database_sync_to_async
    def _mark_seen(user_id):
        from django.contrib.auth import get_user_model

        from accounts.services import mark_seen

        return mark_seen(get_user_model().objects.get(pk=user_id))

    @staticmethod
    @database_sync_to_async
    def _notify_event_created(event):
        from notifications import services as notification_services
        from notifications.models import Notification

        members = (
            event.room.memberships.select_related("user")
            .exclude(user=event.created_by)
            .all()
        )
        for membership in members:
            notification_services.create_notification(
                membership.user,
                f"New event '{event.title}' in '{event.room.name}'",
                Notification.Type.EVENT_CREATED,
                actor=event.created_by,
                room=event.room,
            )

    def _fake_request(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        request = APIRequestFactory().get("/")
        request.user = self.user
        return Request(request)