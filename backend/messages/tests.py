"""GeoConnect messages: REST test suite (history + send)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from messages.models import RoomMessage
from rooms.models import Room, RoomMember

User = get_user_model()


class MessageTestBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", "owner@example.com", "SecretPass123!")
        self.member = User.objects.create_user("member", "member@example.com", "SecretPass123!")
        self.room = Room.objects.create(name="Chat Room", created_by=self.owner)
        RoomMember.objects.create(room=self.room, user=self.owner, role=RoomMember.Role.OWNER)
        RoomMember.objects.create(room=self.room, user=self.member, role=RoomMember.Role.MEMBER)


class MessageTests(MessageTestBase):
    def test_send_and_list(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            f"/api/rooms/{self.room.id}/messages/",
            {"content": "hello"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["sender_id"], self.owner.id)

        history = self.client.get(f"/api/rooms/{self.room.id}/messages/")
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(len(history.data), 1)
        self.assertEqual(history.data[0]["content"], "hello")

    def test_empty_message_rejected(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/rooms/{self.room.id}/messages/", {"content": "   "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_overlong_message_rejected(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/rooms/{self.room.id}/messages/", {"content": "x" * 2001}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_pagination(self):
        self.client.force_authenticate(self.owner)
        for index in range(40):
            RoomMessage.objects.create(room=self.room, sender=self.owner, content=f"m{index}")
        response = self.client.get(f"/api/rooms/{self.room.id}/messages/?limit=20")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 20)
        self.assertEqual(response.data[0]["content"], "m20")
        self.assertEqual(response.data[-1]["content"], "m39")

    def test_oldest_first_ordering(self):
        self.client.force_authenticate(self.owner)
        RoomMessage.objects.create(room=self.room, sender=self.owner, content="first")
        RoomMessage.objects.create(room=self.room, sender=self.member, content="second")
        response = self.client.get(f"/api/rooms/{self.room.id}/messages/")
        self.assertEqual([m["content"] for m in response.data], ["first", "second"])

    def test_non_member_cannot_send(self):
        self.client.force_authenticate(
            User.objects.create_user("outsider", "outsider@example.com", "SecretPass123!")
        )
        response = self.client.post(
            f"/api/rooms/{self.room.id}/messages/", {"content": "hi"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)