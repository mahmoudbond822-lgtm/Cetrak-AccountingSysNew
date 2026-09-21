import pytest
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth.hashers import identify_hasher, make_password

from apps.accounts.models import User, Membership
from apps.accounts.serializers import UserSerializer, MemberSerializer
from apps.accounts.tests import helpers as test_helpers


class PasswordHashingTests(APITestCase):
    def register(self, email="user@example.com", password="SecurePass123"):
        url = reverse("auth-register")
        data = {
            "email": email,
            "password": password,
            "company_name": "Test Corp",
        }
        return self.client.post(url, data, format="json")

    def test_new_password_is_stored_as_bcrypt_hash(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        assert user.password != "SecurePass123"
        assert identify_hasher(user.password).algorithm == "bcrypt_sha256"

    def test_stored_hash_is_not_plaintext(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        assert "SecurePass123" not in user.password
        assert user.password.startswith("bcrypt_sha256$")

    def test_correct_password_authenticates(self):
        self.register()
        response = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_wrong_password_gets_401(self):
        self.register()
        response = test_helpers.login(self.client, "user@example.com", "WrongPass123")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_response_does_not_contain_password(self):
        self.register()
        response = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        assert "password" not in response.data
        assert "password" not in response.data["user"]

    def test_register_response_does_not_contain_password(self):
        response = self.register()
        assert "password" not in response.data
        assert "password" not in response.data["user"]

    def test_me_response_does_not_contain_password(self):
        self.register()
        login_resp = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        response = self.client.get(
            reverse("auth-me"),
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "password" not in response.data

    def test_user_serializer_excludes_password(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        data = UserSerializer(user).data
        assert "password" not in data

    def test_member_serializer_excludes_password(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        membership = Membership.objects.get(user=user)
        data = MemberSerializer(membership).data
        assert "password" not in data

    def test_create_user_uses_configured_primary_hasher(self):
        user = User.objects.create_user(
            email="direct@example.com", password="SecurePass123"
        )
        assert identify_hasher(user.password).algorithm == "bcrypt_sha256"

    def test_pbkdf2_hash_remains_verifiable(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        user.password = make_password("SecurePass123", hasher="pbkdf2_sha256")
        user.save()

        response = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        assert response.status_code == status.HTTP_200_OK

    def test_legacy_hash_upgrades_to_bcrypt_after_successful_login(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        user.password = make_password("SecurePass123", hasher="pbkdf2_sha256")
        user.save()

        assert identify_hasher(user.password).algorithm == "pbkdf2_sha256"
        response = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert identify_hasher(user.password).algorithm == "bcrypt_sha256"

    def test_failed_login_does_not_upgrade_legacy_hash(self):
        self.register()
        user = User.objects.get(email="user@example.com")
        user.password = make_password("SecurePass123", hasher="pbkdf2_sha256")
        user.save()

        response = test_helpers.login(self.client, "user@example.com", "WrongPass123")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        user.refresh_from_db()
        assert identify_hasher(user.password).algorithm == "pbkdf2_sha256"

    def test_login_error_does_not_contain_password(self):
        self.register()
        response = test_helpers.login(self.client, "user@example.com", "WrongPass123")
        assert "WrongPass123" not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_default_hasher_is_bcrypt_sha256():
    from django.contrib.auth.hashers import get_hasher

    hasher = get_hasher()
    assert hasher.algorithm == "bcrypt_sha256"
    assert hasher.rounds == 12