"""GeoConnect WebSocket consumer tests.

Covers the three real-time endpoints through the URL router:
  /ws/rooms/<id>/       RoomConsumer  (snapshot, chat, presence, event/marker)
  /ws/location/<id>/    LocationConsumer (location_update / location_stopped)
  /ws/notifications/    NotificationConsumer (inbox push)

Each scenario runs inside a single event loop (asyncio.run) so the in-memory
channel layer can deliver messages between all communicators in that test.
A TransactionTestCase is used so writes made from synchronous helper code are
committed and visible to the assert statements on the main thread.
"""

import asyncio

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from notifications import services as notification_services
from notifications.models import Notification
from rooms.models import Room, RoomMember

User = get_user_model()

IN_MEMORY_LAYER = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

import config.routing  # noqa: E402


def ws_application(user):
    """URL router with the authenticated user pre-injected into the scope."""

    async def application(scope, receive, send):
        scope["user"] = user
        return await URLRouter(config.routing.websocket_urlpatterns)(scope, receive, send)

    return application


def is_rejected(result):
    """connect() may return False or a (False, reason) tuple on rejection."""
    if result is False:
        return True
    return isinstance(result, (tuple, list)) and len(result) > 0 and result[0] is False


class RoomConsumerTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user("ws_owner", "ws_owner@example.com", "SecretPass123!")
        self.member = User.objects.create_user("ws_member", "ws_member@example.com", "SecretPass123!")
        self.room = Room.objects.create(name="WS Room", created_by=self.owner)
        RoomMember.objects.create(room=self.room, user=self.owner, role=RoomMember.Role.OWNER)
        RoomMember.objects.create(room=self.room, user=self.member, role=RoomMember.Role.MEMBER)

    def _room_comms(self, *users):
        return [
            WebsocketCommunicator(ws_application(user), f"/ws/rooms/{self.room.id}/")
            for user in users
        ]

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_room_snapshot_and_chat(self):
        async def scenario():
            owner_comm, member_comm = self._room_comms(self.owner, self.member)

            self.assertTrue(await owner_comm.connect())

            snapshot = await owner_comm.receive_json_from()
            self.assertEqual(snapshot["type"], "room_snapshot")
            self.assertEqual(snapshot["my_role"], RoomMember.Role.OWNER)
            self.assertEqual(len(snapshot["participants"]), 2)

            self.assertTrue(await member_comm.connect())

            joined = None
            for _ in range(5):
                msg = await owner_comm.receive_json_from()
                if msg["type"] == "user_joined" and msg["user"]["user_id"] == self.member.id:
                    joined = msg
                    break
            self.assertIsNotNone(joined)

            await member_comm.send_json_to({"type": "chat_message", "content": "ping"})
            chat = None
            for _ in range(6):
                msg = await owner_comm.receive_json_from()
                if msg["type"] == "chat_message":
                    chat = msg
                    break
            self.assertIsNotNone(chat)
            self.assertEqual(chat["message"]["content"], "ping")
            self.assertEqual(chat["message"]["sender_id"], self.member.id)

            await owner_comm.disconnect()
            await member_comm.disconnect()

        asyncio.run(scenario())

        from messages.models import RoomMessage

        self.assertTrue(RoomMessage.objects.filter(room=self.room, content="ping").exists())

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_event_created_via_socket(self):
        async def scenario():
            owner_comm, member_comm = self._room_comms(self.owner, self.member)
            await owner_comm.connect()
            await member_comm.connect()

            await member_comm.send_json_to(
                {
                    "type": "event_created",
                    "title": "Socket party",
                    "description": "online",
                    "latitude": 40.0,
                    "longitude": 5.0,
                    "start_time": (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
                }
            )
            received = None
            for _ in range(6):
                msg = await owner_comm.receive_json_from()
                if msg["type"] == "event_created":
                    received = msg
                    break
            self.assertIsNotNone(received)
            self.assertEqual(received["event"]["title"], "Socket party")

            await owner_comm.disconnect()
            await member_comm.disconnect()

        asyncio.run(scenario())

        from events.models import LocationEvent

        self.assertTrue(LocationEvent.objects.filter(title="Socket party").exists())
        self.assertTrue(
            Notification.objects.filter(user=self.owner, type=Notification.Type.EVENT_CREATED).exists()
        )

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_marker_created_via_socket(self):
        async def scenario():
            comm = self._room_comms(self.owner)[0]
            await comm.connect()

            await comm.send_json_to(
                {
                    "type": "marker_created",
                    "title": "Cache",
                    "marker_type": "important",
                    "latitude": 41.0,
                    "longitude": 6.0,
                }
            )
            received = None
            for _ in range(6):
                msg = await comm.receive_json_from()
                if msg["type"] == "marker_created":
                    received = msg
                    break
            self.assertIsNotNone(received)
            self.assertEqual(received["marker"]["title"], "Cache")
            await comm.disconnect()

        asyncio.run(scenario())

        from locations.models import MapMarker

        self.assertTrue(MapMarker.objects.filter(title="Cache").exists())

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_non_member_is_rejected(self):
        outsider = User.objects.create_user("ws_out", "ws_out@example.com", "SecretPass123!")

        async def scenario():
            comm = WebsocketCommunicator(ws_application(outsider), f"/ws/rooms/{self.room.id}/")
            connected = await comm.connect()
            self.assertTrue(is_rejected(connected))

        asyncio.run(scenario())


class LocationConsumerTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user("lc_owner", "lc_owner@example.com", "SecretPass123!")
        self.member = User.objects.create_user("lc_member", "lc_member@example.com", "SecretPass123!")
        self.room = Room.objects.create(name="LC Room", created_by=self.owner)
        RoomMember.objects.create(room=self.room, user=self.owner, role=RoomMember.Role.OWNER)
        RoomMember.objects.create(room=self.room, user=self.member, role=RoomMember.Role.MEMBER)

    def _comms(self, *users):
        return [
            WebsocketCommunicator(ws_application(user), f"/ws/location/{self.room.id}/")
            for user in users
        ]

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_location_share_and_stop(self):
        async def scenario():
            owner_comm, member_comm = self._comms(self.owner, self.member)
            self.assertTrue(await owner_comm.connect())
            self.assertTrue(await member_comm.connect())

            await member_comm.send_json_to(
                {"type": "location_update", "latitude": 48.8584, "longitude": 2.2945, "accuracy": 6.0}
            )
            update = None
            for _ in range(5):
                msg = await owner_comm.receive_json_from()
                if msg["type"] == "location_update":
                    update = msg
                    break
            self.assertIsNotNone(update)
            self.assertAlmostEqual(update["latitude"], 48.8584)
            self.assertAlmostEqual(update["longitude"], 2.2945)
            self.assertEqual(update["user"]["user_id"], self.member.id)

            await member_comm.send_json_to({"type": "stop_sharing"})
            stopped = None
            for _ in range(5):
                msg = await owner_comm.receive_json_from()
                if msg["type"] == "location_stopped":
                    stopped = msg
                    break
            self.assertIsNotNone(stopped)
            self.assertEqual(stopped["user"]["user_id"], self.member.id)

            await owner_comm.disconnect()
            await member_comm.disconnect()

        asyncio.run(scenario())

        self.member.profile.refresh_from_db()
        self.assertFalse(self.member.profile.is_sharing_location)

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_bad_coordinates_rejected(self):
        async def scenario():
            comm = self._comms(self.member)[0]
            await comm.connect()

            await comm.send_json_to(
                {"type": "location_update", "latitude": 999, "longitude": 2.2945}
            )
            err = None
            for _ in range(3):
                msg = await comm.receive_json_from()
                if msg["type"] == "error":
                    err = msg
                    break
            self.assertIsNotNone(err)
            await comm.disconnect()

        asyncio.run(scenario())

        self.member.profile.refresh_from_db()
        self.assertFalse(self.member.profile.is_sharing_location)


class NotificationConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user("nc_user", "nc_user@example.com", "SecretPass123!")

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_pushed_notification(self):
        async def scenario():
            comm = WebsocketCommunicator(ws_application(self.user), "/ws/notifications/")
            self.assertTrue(await comm.connect())

            await sync_to_async(notification_services.create_notification)(
                self.user, "You have mail", Notification.Type.SYSTEM
            )

            frame = None
            for _ in range(3):
                msg = await comm.receive_json_from()
                if msg["type"] == "notification":
                    frame = msg
                    break
            self.assertIsNotNone(frame)
            self.assertEqual(frame["message"], "You have mail")
            self.assertEqual(frame["type_name"], "system")
            self.assertFalse(frame["is_read"])
            await comm.disconnect()

        asyncio.run(scenario())

    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_unauthenticated_rejected(self):
        class Anon:
            is_authenticated = False
            id = None

        async def scenario():
            comm = WebsocketCommunicator(ws_application(Anon()), "/ws/notifications/")
            connected = await comm.connect()
            self.assertTrue(is_rejected(connected))

        asyncio.run(scenario())