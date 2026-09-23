"""GeoConnect locations: REST test suite (markers, locations, nearby, sharing)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from locations.models import MapMarker, UserLocation
from rooms.models import Room, RoomMember

User = get_user_model()


class LocationTestBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", "owner@example.com", "SecretPass123!")
        self.member = User.objects.create_user("member", "member@example.com", "SecretPass123!")
        self.room = Room.objects.create(name="Map Room", created_by=self.owner)
        RoomMember.objects.create(room=self.room, user=self.owner, role=RoomMember.Role.OWNER)
        RoomMember.objects.create(room=self.room, user=self.member, role=RoomMember.Role.MEMBER)


class MarkerTests(LocationTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.owner)

    def _create(self, **overrides):
        payload = {
            "title": "Fire exit",
            "marker_type": "danger",
            "latitude": 51.505,
            "longitude": -0.09,
        }
        payload.update(overrides)
        return self.client.post(
            f"/api/rooms/{self.room.id}/markers/", payload, format="json"
        )

    def test_create_and_list_marker(self):
        created = self._create()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["created_by_id"], self.owner.id)

        listed = self.client.get(f"/api/rooms/{self.room.id}/markers/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data), 1)

    def test_rejects_invalid_marker_type(self):
        response = self._create(marker_type="nope")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_bad_coordinates(self):
        response = self._create(latitude=95.0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_can_update_marker_they_created(self):
        self.client.force_authenticate(self.member)
        created = self._create()
        marker_id = created.data["id"]
        response = self.client.patch(
            f"/api/rooms/{self.room.id}/markers/{marker_id}/",
            {"title": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_cannot_delete_others_marker(self):
        created = self._create()
        marker_id = created.data["id"]
        self.client.force_authenticate(self.member)
        response = self.client.delete(f"/api/rooms/{self.room.id}/markers/{marker_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_any_marker(self):
        created = self._create()
        marker_id = created.data["id"]
        RoomMember.objects.filter(room=self.room, user=self.member).update(
            role=RoomMember.Role.ADMIN
        )
        self.client.force_authenticate(self.member)
        response = self.client.delete(f"/api/rooms/{self.room.id}/markers/{marker_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MapMarker.objects.filter(pk=marker_id).exists())


class LocationSharingTests(LocationTestBase):
    def test_locations_only_show_sharing_members(self):
        UserLocation.objects.create(
            user=self.owner,
            latitude=51.5,
            longitude=-0.09,
            accuracy=5.0,
        )
        # owner not sharing -> hidden
        self.client.force_authenticate(self.member)
        response = self.client.get(f"/api/rooms/{self.room.id}/locations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        self.owner.profile.is_sharing_location = True
        self.owner.profile.save()
        response = self.client.get(f"/api/rooms/{self.room.id}/locations/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"]["user_id"], self.owner.id)

    def test_nearby_requires_caller_sharing(self):
        UserLocation.objects.create(
            user=self.owner,
            latitude=51.505,
            longitude=-0.09,
            accuracy=5.0,
        )
        self.owner.profile.is_sharing_location = True
        self.owner.profile.save()

        self.client.force_authenticate(self.member)
        response = self.client.get(f"/api/rooms/{self.room.id}/nearby/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "needs_location")

    def test_nearby_lists_other_sharing_members(self):
        UserLocation.objects.create(
            user=self.owner,
            latitude=51.505,
            longitude=-0.09,
            accuracy=5.0,
        )
        self.owner.profile.is_sharing_location = True
        self.owner.profile.save()
        UserLocation.objects.create(
            user=self.member,
            latitude=51.5055,
            longitude=-0.09,
            accuracy=4.0,
        )
        self.member.profile.is_sharing_location = True
        self.member.profile.save()

        self.client.force_authenticate(self.member)
        response = self.client.get(f"/api/rooms/{self.room.id}/nearby/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["nearby"]), 1)
        self.assertEqual(response.data["nearby"][0]["user"]["user_id"], self.owner.id)
        self.assertIn("distance_m", response.data["nearby"][0])
        self.assertGreater(response.data["nearby"][0]["distance_m"], 0)

    def test_update_user_location_enables_sharing(self):
        from locations import services

        location, just_enabled = services.update_user_location(self.owner, 10.0, 20.0, 3.0)
        self.assertTrue(just_enabled)
        self.owner.profile.refresh_from_db()
        self.assertTrue(self.owner.profile.is_sharing_location)
        self.assertEqual(location.latitude, 10.0)

    def test_set_location_sharing_off(self):
        from locations import services

        services.update_user_location(self.owner, 10.0, 20.0, 3.0)
        services.set_location_sharing(self.owner, False)
        self.owner.profile.refresh_from_db()
        self.assertFalse(self.owner.profile.is_sharing_location)
        # last-known coordinate stays on disk (privacy: no history but location persists)
        self.assertTrue(UserLocation.objects.filter(user=self.owner).exists())