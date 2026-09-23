"""GeoConnect rooms: REST test suite (lifecycle, roles, permissions, search)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from notifications.models import Notification
from rooms.models import Room, RoomMember

User = get_user_model()


class RoomTestBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", "owner@example.com", "SecretPass123!")
        self.member = User.objects.create_user("member", "member@example.com", "SecretPass123!")
        self.stranger = User.objects.create_user("stranger", "stranger@example.com", "SecretPass123!")
        self.room = Room.objects.create(name="Base Room", created_by=self.owner)
        RoomMember.objects.create(room=self.room, user=self.owner, role=RoomMember.Role.OWNER)
        RoomMember.objects.create(room=self.room, user=self.member, role=RoomMember.Role.MEMBER)


class RoomLifecycleTests(RoomTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.owner)

    def test_create_room_makes_owner(self):
        response = self.client.post(
            "/api/rooms/", {"name": "New", "description": "desc", "is_private": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = Room.objects.get(pk=response.data["id"])
        self.assertEqual(room.created_by, self.owner)
        self.assertEqual(room.is_private, True)

    def test_create_room_requires_name(self):
        response = self.client.post("/api/rooms/", {"name": "  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_my_rooms(self):
        response = self.client.get("/api/rooms/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["my_role"], RoomMember.Role.OWNER)
        self.assertEqual(response.data[0]["member_count"], 2)

    def test_get_room_detail_for_member(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(f"/api/rooms/{self.room.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["member_count"], 2)

    def test_non_member_gets_404(self):
        self.client.force_authenticate(self.stranger)
        response = self.client.get(f"/api/rooms/{self.room.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_room_404(self):
        response = self.client.get("/api/rooms/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class JoinLeaveTests(RoomTestBase):
    def test_join_public_room(self):
        self.client.force_authenticate(self.stranger)
        response = self.client.post(f"/api/rooms/{self.room.id}/join/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            RoomMember.objects.filter(room=self.room, user=self.stranger).exists()
        )

    def test_join_private_room_requires_invite(self):
        self.room.is_private = True
        self.room.save()
        self.client.force_authenticate(self.stranger)
        response = self.client.post(f"/api/rooms/{self.room.id}/join/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            RoomMember.objects.filter(room=self.room, user=self.stranger).exists()
        )

    def test_owner_cannot_leave(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/rooms/{self.room.id}/leave/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_leaves(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(f"/api/rooms/{self.room.id}/leave/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            RoomMember.objects.filter(room=self.room, user=self.member).exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=self.owner, type=Notification.Type.USER_LEFT).exists()
        )

    def test_leave_deletes_owned_rooms_guard(self):
        solo = Room.objects.create(name="Solo", created_by=self.stranger)
        RoomMember.objects.create(room=solo, user=self.stranger, role=RoomMember.Role.OWNER)
        self.client.force_authenticate(self.stranger)
        response = self.client.post(f"/api/rooms/{solo.id}/leave/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RoleAndMemberTests(RoomTestBase):
    def _promote(self, client_user, target_user, role):
        self.client.force_authenticate(client_user)
        return self.client.patch(
            f"/api/rooms/{self.room.id}/members/{target_user.id}/",
            {"role": role},
            format="json",
        )

    def test_owner_promotes_member_to_admin(self):
        response = self._promote(self.owner, self.member, RoomMember.Role.ADMIN)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            RoomMember.objects.get(room=self.room, user=self.member).role, RoomMember.Role.ADMIN
        )

    def test_cannot_promote_to_owner(self):
        response = self._promote(self.owner, self.member, RoomMember.Role.OWNER)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_change_roles(self):
        response = self._promote(self.member, self.owner, RoomMember.Role.MEMBER)
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_admin_cannot_change_same_level(self):
        other_admin = User.objects.create_user("o2", "o2@example.com", "SecretPass123!")
        RoomMember.objects.create(
            room=self.room, user=other_admin, role=RoomMember.Role.ADMIN
        )
        RoomMember.objects.filter(room=self.room, user=self.member).update(
            role=RoomMember.Role.ADMIN
        )
        response = self._promote(other_admin, self.member, RoomMember.Role.MEMBER)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_cannot_be_removed(self):
        self.client.force_authenticate(self.member)
        response = self.client.delete(f"/api/rooms/{self.room.id}/members/{self.owner.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_removes_member(self):
        RoomMember.objects.create(
            room=self.room, user=self.stranger, role=RoomMember.Role.MEMBER
        )
        RoomMember.objects.filter(room=self.room, user=self.member).update(
            role=RoomMember.Role.ADMIN
        )
        self.client.force_authenticate(self.member)
        response = self.client.delete(
            f"/api/rooms/{self.room.id}/members/{self.stranger.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            RoomMember.objects.filter(room=self.room, user=self.stranger).exists()
        )

    def test_add_member_by_username(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/rooms/{self.room.id}/members/",
            {"username": "member"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreaterEqual(
            RoomMember.objects.filter(room=self.room).count(), 2
        )

    def test_add_unknown_username_404(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/rooms/{self.room.id}/members/", {"username": "ghost"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_members_list(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/rooms/{self.room.id}/members/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class RoomManagementTests(RoomTestBase):
    def test_owner_updates_room(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/rooms/{self.room.id}/", {"name": "Renamed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.name, "Renamed")

    def test_member_cannot_update_room(self):
        self.client.force_authenticate(self.member)
        response = self.client.patch(
            f"/api/rooms/{self.room.id}/", {"name": "Nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_owner_deletes_room(self):
        self.client.force_authenticate(self.member)
        response = self.client.delete(f"/api/rooms/{self.room.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/rooms/{self.room.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(pk=self.room.id).exists())
        self.assertTrue(
            Notification.objects.filter(
                user=self.member, type=Notification.Type.ROOM_DELETED
            ).exists()
        )


class SearchTests(RoomTestBase):
    def test_search_rooms_of_user(self):
        Room.objects.create(name="Hidden room", created_by=self.stranger)
        self.client.force_authenticate(self.owner)
        response = self.client.get(f"/api/rooms/search/?q={self.room.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rooms = response.data["rooms"]
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["id"], self.room.id)

    def test_empty_query_returns_empty_buckets(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/rooms/search/?q=")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rooms"], [])