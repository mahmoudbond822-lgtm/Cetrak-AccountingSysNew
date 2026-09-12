import pytest
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.accounts.tests import helpers as test_helpers


class RegisterTests(APITestCase):
    def test_register_success_returns_201_with_tokens(self):
        url = reverse("auth-register")
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "company_name": "Test Corp",
        }
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" not in response.data
        assert response.data["user"]["email"] == "user@example.com"
        assert response.data["tenant"]["name"] == "Test Corp"
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"].value
        assert response.cookies["refresh_token"]["httponly"]

    def test_register_duplicate_email_returns_400(self):
        url = reverse("auth-register")
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "company_name": "Test Corp",
        }
        self.client.post(url, data, format="json")
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class LoginTests(APITestCase):
    def setUp(self):
        url = reverse("auth-register")
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "company_name": "Test Corp",
        }
        self.client.post(url, data, format="json")

    def test_login_success_returns_200_with_tokens(self):
        url = reverse("auth-login")
        data = {"email": "user@example.com", "password": "SecurePass123"}
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" not in response.data
        assert len(response.data["tenants"]) == 1
        assert response.data["active_tenant"] is not None
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"].value

    def test_login_wrong_password_returns_401(self):
        url = reverse("auth-login")
        data = {"email": "user@example.com", "password": "WrongPass123"}
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_disabled_user_returns_403(self):
        from apps.accounts.models import User

        user = User.objects.get(email="user@example.com")
        user.status = User.Status.DISABLED
        user.save()

        url = reverse("auth-login")
        data = {"email": "user@example.com", "password": "SecurePass123"}
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TokenRefreshTests(APITestCase):
    def setUp(self):
        url = reverse("auth-register")
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "company_name": "Test Corp",
        }
        self.client.post(url, data, format="json")

    def test_token_refresh_returns_new_access_token(self):
        login_resp = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        assert login_resp.status_code == status.HTTP_200_OK
        assert "refresh_token" in self.client.cookies

        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" not in response.data


class TokenRotationTests(APITestCase):
    def setUp(self):
        url = reverse("auth-register")
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "company_name": "Test Corp",
        }
        self.client.post(url, data, format="json")
        login_resp = test_helpers.login(self.client, "user@example.com", "SecurePass123")
        self.refresh_token = test_helpers.refresh_cookie_value(self.client)
        self.refresh_url = reverse("auth-refresh")

    def test_refresh_returns_new_access_and_rotates_cookie(self):
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" not in response.data
        rotated = test_helpers.refresh_cookie_value(self.client)
        assert rotated != self.refresh_token

    def test_old_refresh_blacklisted_after_rotation(self):
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        old = self.refresh_token

        self.client.cookies["refresh_token"] = old
        reuse = test_helpers.post_refresh(self.client)
        assert reuse.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rotated_refresh_token_can_be_reused_exactly_once(self):
        first = test_helpers.post_refresh(self.client)
        assert first.status_code == status.HTTP_200_OK
        rotated = test_helpers.refresh_cookie_value(self.client)

        second = test_helpers.post_refresh(self.client)
        assert second.status_code == status.HTTP_200_OK
        assert test_helpers.refresh_cookie_value(self.client) != rotated

        self.client.cookies["refresh_token"] = rotated
        third = test_helpers.post_refresh(self.client)
        assert third.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_after_rotation_issues_working_access_token(self):
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        access = response.data["access"]

        me_url = reverse("auth-me")
        me_resp = self.client.get(
            me_url, HTTP_AUTHORIZATION=f"Bearer {access}"
        )
        assert me_resp.status_code == status.HTTP_200_OK


class LogoutTests(APITestCase):
    def setUp(self):
        url = reverse("auth-register")
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "company_name": "Test Corp",
        }
        self.client.post(url, data, format="json")
        test_helpers.login(self.client, "user@example.com", "SecurePass123")
        self.refresh_token = test_helpers.refresh_cookie_value(self.client)

    def test_logout_returns_205_and_clears_cookie(self):
        response = test_helpers.post_logout(self.client)
        assert response.status_code == status.HTTP_205_RESET_CONTENT
        assert test_helpers.refresh_cookie_value(self.client) == ""

    def test_logout_blacklisted_token_cannot_refresh(self):
        test_helpers.post_logout(self.client)
        self.client.cookies["refresh_token"] = self.refresh_token
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class ProtectedEndpointTests(APITestCase):
    def test_protected_endpoint_without_token_returns_401(self):
        url = reverse("auth-me")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TenantIsolationTests(APITestCase):
    def test_tenant_isolation(self):
        url = reverse("auth-register")
        self.client.post(
            url,
            {"email": "userA@example.com", "password": "Pass1234", "company_name": "TenantA"},
            format="json",
        )
        self.client.post(
            url,
            {"email": "userB@example.com", "password": "Pass1234", "company_name": "TenantB"},
            format="json",
        )
        login_url = reverse("auth-login")
        resp_a = self.client.post(
            login_url, {"email": "userA@example.com", "password": "Pass1234"}, format="json"
        )
        assert resp_a.data["active_tenant"]["name"] == "TenantA"
        assert resp_a.data["active_tenant"]["name"] != "TenantB"
