from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from apps.accounts.cookies import refresh_cookie_kwargs
from apps.accounts.tests import helpers as test_helpers


class RefreshCookieTests(APITestCase):
    def setUp(self):
        url = reverse("auth-register")
        self.client.post(
            url,
            {"email": "user@example.com", "password": "SecurePass123", "company_name": "Corp"},
            format="json",
        )
        self.login_resp = test_helpers.login(
            self.client, "user@example.com", "SecurePass123"
        )
        self.refresh_url = reverse("auth-refresh")

    def test_login_sets_httponly_refresh_cookie(self):
        response = self.login_resp
        assert response.status_code == status.HTTP_200_OK
        assert "refresh" not in response.data
        cookie = response.cookies["refresh_token"]
        assert cookie.value
        assert cookie["httponly"]
        assert cookie["path"] == "/api/v1/"
        assert cookie["samesite"] == "Lax"
        assert int(cookie["max-age"]) == 604800

    def test_refresh_via_cookie_returns_access_and_rotates_cookie(self):
        old = test_helpers.refresh_cookie_value(self.client)
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" not in response.data
        new = test_helpers.refresh_cookie_value(self.client)
        assert new != old

    def test_refresh_without_cookie_returns_401(self):
        del self.client.cookies["refresh_token"]
        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_without_csrf_header_returns_403(self):
        response = self.client.post(self.refresh_url, {}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_refresh_with_wrong_csrf_header_returns_403(self):
        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN="totally-wrong-token",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_logout_clears_refresh_cookie_and_returns_205(self):
        response = test_helpers.post_logout(self.client)
        assert response.status_code == status.HTTP_205_RESET_CONTENT
        assert test_helpers.refresh_cookie_value(self.client) == ""

    def test_logout_without_csrf_header_returns_403(self):
        response = self.client.post(reverse("auth-logout"), {}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_refresh_preserves_remember_me_lifetime(self):
        self.client.post(
            reverse("auth-login"),
            {"email": "user@example.com", "password": "SecurePass123", "remember_me": True},
            format="json",
        )
        assert int(self.client.cookies["refresh_token"]["max-age"]) == 2592000

        response = test_helpers.post_refresh(self.client)
        assert response.status_code == status.HTTP_200_OK
        assert int(self.client.cookies["refresh_token"]["max-age"]) == 2592000

    def test_refresh_cookie_kwargs_production_configuration(self):
        kwargs = refresh_cookie_kwargs(secure=True)
        assert kwargs["secure"] is True
        assert kwargs["httponly"] is True
        assert kwargs["path"] == "/api/v1/"
        assert kwargs["samesite"] == "Lax"
        assert kwargs["max_age"] == 604800

        remember_me_kwargs = refresh_cookie_kwargs(remember_me=True, secure=True)
        assert remember_me_kwargs["max_age"] == 2592000

    def test_prod_settings_force_secure_refresh_cookie(self):
        import os
        import sys

        os.environ["DJANGO_SECRET_KEY"] = "prod-test-secret-key"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://example.com")
        os.environ.setdefault("CSRF_TRUSTED_ORIGINS", "https://example.com")

        sys.modules.pop("config.settings.base", None)
        sys.modules.pop("config.settings.prod", None)
        import importlib

        prod = importlib.import_module("config.settings.prod")

        assert prod.REFRESH_COOKIE_SECURE is True
        assert prod.CORS_ALLOW_CREDENTIALS is True
        assert "x-csrf-token" in prod.CORS_ALLOW_HEADERS
        assert "apps.core.middleware.SecurityHeadersMiddleware" in prod.MIDDLEWARE