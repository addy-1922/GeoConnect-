"""GeoConnect accounts: REST test suite (register / login / logout / me / search)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class RegisterLoginTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.creds = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "ComplexPass123!",
            "password_confirm": "ComplexPass123!",
        }

    def test_register_returns_user_and_csrf(self):
        response = self.client.post("/api/auth/register/", self.creds, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["username"], "alice")
        self.assertIn("csrfToken", response.data)
        self.assertTrue(response.data["user"].get("user_id"))

    def test_register_rejects_mismatched_passwords(self):
        bad = {**self.creds, "password_confirm": "Different123!"}
        response = self.client.post("/api/auth/register/", bad, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_duplicate_username_and_email(self):
        self.client.post("/api/auth/register/", self.creds, format="json")
        response = self.client.post("/api/auth/register/", self.creds, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success_and_failure(self):
        User.objects.create_user("bob", "bob@example.com", "SecretPass123!")
        ok = self.client.post(
            "/api/auth/login/", {"username": "bob", "password": "SecretPass123!"}, format="json"
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        bad = self.client.post(
            "/api/auth/login/", {"username": "bob", "password": "nope"}, format="json"
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_csrf_endpoint(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.data)


class MeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("carol", "carol@example.com", "SecretPass123!")
        self.client.force_authenticate(self.user)

    def test_get_me(self):
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "carol")
        self.assertEqual(response.data["user_id"], self.user.id)

    def test_update_me_status(self):
        response = self.client.patch("/api/users/me/", {"status": "online"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "online")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.status, "online")

    def test_unauthenticated_me_rejected(self):
        client = APIClient()
        response = client.get("/api/users/me/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserSearchTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("dave", "dave@example.com", "SecretPass123!")
        User.objects.create_user("dan", "dan@example.com", "SecretPass123!")
        self.client.force_authenticate(self.user)

    def test_search_by_substring(self):
        response = self.client.get("/api/users/?search=da")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = {u["username"] for u in response.data}
        self.assertEqual(usernames, {"dave", "dan"})

    def test_search_requires_auth(self):
        response = APIClient().get("/api/users/?search=d")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)