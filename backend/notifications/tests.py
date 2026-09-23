"""GeoConnect notifications: REST test suite."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from notifications import services
from notifications.models import Notification

User = get_user_model()


class NotificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("n1", "n1@example.com", "SecretPass123!")
        self.other = User.objects.create_user("n2", "n2@example.com", "SecretPass123!")
        self.client.force_authenticate(self.user)

    def test_create_and_list(self):
        services.create_notification(
            self.user, "Hello there", Notification.Type.SYSTEM, actor=self.other
        )
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["actor_username"], "n2")
        self.assertFalse(response.data[0]["is_read"])

    def test_unread_count(self):
        services.create_notification(self.user, "a", Notification.Type.SYSTEM)
        services.create_notification(self.user, "b", Notification.Type.SYSTEM)
        one = Notification.objects.get(user=self.user, message="a")
        Notification.objects.filter(pk=one.pk).update(is_read=True)

        response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_mark_one_read(self):
        services.create_notification(self.user, "a", Notification.Type.SYSTEM)
        one = Notification.objects.get(user=self.user, message="a")
        response = self.client.post(f"/api/notifications/{one.id}/read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        one.refresh_from_db()
        self.assertTrue(one.is_read)

    def test_mark_all_read(self):
        services.create_notification(self.user, "a", Notification.Type.SYSTEM)
        services.create_notification(self.user, "b", Notification.Type.SYSTEM)
        response = self.client.post("/api/notifications/mark-all-read/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(), 0
        )

    def test_cannot_read_others_notification(self):
        services.create_notification(self.other, "secret", Notification.Type.SYSTEM)
        hidden = Notification.objects.get(user=self.other)
        response = self.client.post(f"/api/notifications/{hidden.id}/read/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_requires_auth(self):
        response = APIClient().get("/api/notifications/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)