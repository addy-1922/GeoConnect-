"""GeoConnect events: REST test suite (create, list, detail, permissions)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from events.models import LocationEvent
from notifications.models import Notification
from rooms.models import Room, RoomMember

User = get_user_model()


class EventTestBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", "owner@example.com", "SecretPass123!")
        self.member = User.objects.create_user("member", "member@example.com", "SecretPass123!")
        self.room = Room.objects.create(name="Event Room", created_by=self.owner)
        RoomMember.objects.create(room=self.room, user=self.owner, role=RoomMember.Role.OWNER)
        RoomMember.objects.create(room=self.room, user=self.member, role=RoomMember.Role.MEMBER)


class EventTests(EventTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.owner)

    def _create(self, **overrides):
        payload = {
            "title": "Team lunch",
            "description": "at the park",
            "latitude": 51.51,
            "longitude": -0.08,
            "start_time": None,
        }
        payload.update(overrides)
        return self.client.post(
            f"/api/rooms/{self.room.id}/events/", payload, format="json"
        )

    def test_create_event_notifies_others(self):
        created = self._create()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["created_by_id"], self.owner.id)
        self.assertTrue(
            Notification.objects.filter(
                user=self.member, type=Notification.Type.EVENT_CREATED
            ).exists()
        )

    def test_list_events(self):
        self._create()
        response = self.client.get(f"/api/rooms/{self.room.id}/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_requires_title(self):
        response = self._create(title="  ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_past_start_time_rejected(self):
        from django.utils import timezone
        from datetime import timedelta

        response = self._create(start_time=timezone.now() - timedelta(hours=1))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_and_admin_can_delete(self):
        created = self._create()
        event_id = created.data["id"]

        self.client.force_authenticate(self.member)
        member_delete = self.client.delete(f"/api/rooms/{self.room.id}/events/{event_id}/")
        self.assertEqual(member_delete.status_code, status.HTTP_403_FORBIDDEN)

        RoomMember.objects.filter(room=self.room, user=self.member).update(
            role=RoomMember.Role.ADMIN
        )
        admin_delete = self.client.delete(f"/api/rooms/{self.room.id}/events/{event_id}/")
        self.assertEqual(admin_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LocationEvent.objects.filter(pk=event_id).exists())

    def test_non_member_cannot_see_events(self):
        self.client.force_authenticate(
            User.objects.create_user("outsider", "outsider@example.com", "SecretPass123!")
        )
        response = self.client.get(f"/api/rooms/{self.room.id}/events/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)