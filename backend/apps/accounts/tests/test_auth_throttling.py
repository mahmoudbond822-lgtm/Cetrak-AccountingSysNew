"""Authentication throttling on login and refresh (AUD-014).

The throttles are switched off in ``config.settings.test`` so the rest of the
suite behaves as before; every test here re-enables them with
``override_settings`` and drives the real code paths through the API.
"""

import copy
import importlib
import json
import os
import sys
import time
from contextlib import contextmanager
from unittest import mock

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.services import LoginAttemptService
from apps.accounts.tests import helpers as test_helpers
from apps.accounts.throttling import (
    LoginAccountThrottle,
    LoginAddressThrottle,
    RefreshAddressThrottle,
    RefreshSubjectThrottle,
    client_ident,
    throttle_enabled,
)

EMAIL = "user@example.com"
PASSWORD = "SecurePass123"


def throttle_settings(**overrides):
    """AUTH_THROTTLE with the endpoint throttles enabled and ``overrides`` applied."""
    config = copy.deepcopy(settings.AUTH_THROTTLE)
    config["ENABLED"] = True
    config.update(overrides)
    return override_settings(AUTH_THROTTLE=config)


def drf_request(path="/api/v1/auth/login/", data=None, **extra):
    """A DRF request built without going through a view or the database."""
    request = APIRequestFactory().post(path, data or {}, format="json", **extra)
    return Request(request, parsers=[JSONParser()])


def create_company(client, email=EMAIL, password=PASSWORD):
    return client.post(
        reverse("auth-register"),
        {"email": email, "password": password, "company_name": "Test Corp"},
        format="json",
    )


class LoginThrottleTests(APITestCase):
    """POST /auth/login/: address ceiling plus a failed-credential budget."""

    def setUp(self):
        cache.clear()
        self.url = reverse("auth-login")
        create_company(self.client)

    def attempt(self, email=EMAIL, password="wrong-password", **extra):
        return self.client.post(
            self.url, {"email": email, "password": password}, format="json", **extra
        )

    @throttle_settings()
    def test_correct_credentials_are_never_throttled(self):
        for _ in range(3):
            assert self.attempt(password=PASSWORD).status_code == status.HTTP_200_OK

    @throttle_settings()
    def test_wrong_password_keeps_the_existing_generic_401(self):
        response = self.attempt()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "Invalid email or password."

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=3)
    def test_failures_beyond_the_budget_are_refused(self):
        for _ in range(3):
            assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED

        response = self.attempt()

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # The client is told exactly how long to wait, and never less than the
        # window that is left.
        assert 0 < int(response["Retry-After"]) <= 900

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=3)
    def test_refusal_short_circuits_the_password_check(self):
        for _ in range(3):
            self.attempt()

        with mock.patch.object(
            AbstractBaseUser, "check_password", side_effect=AssertionError("hashed")
        ) as check:
            response = self.attempt(password=PASSWORD)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        check.assert_not_called()

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=3)
    def test_refusal_carries_no_account_information(self):
        for _ in range(3):
            self.attempt(email="nobody@example.com")
        unknown = self.attempt(email="nobody@example.com")

        for _ in range(3):
            self.attempt()
        existing = self.attempt()

        # Same shape, same status, no address in the body: an attacker cannot
        # tell a blocked account from a blocked address that never existed.
        assert unknown.status_code == existing.status_code
        assert set(unknown.data) == set(existing.data) == {"detail"}
        assert unknown.data["detail"].startswith("Request was throttled")
        assert EMAIL not in json.dumps(existing.data)
        assert "nobody@example.com" not in json.dumps(unknown.data)

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=3)
    def test_successful_login_clears_the_budget(self):
        assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt(password=PASSWORD).status_code == status.HTTP_200_OK

        # The two attempts below would be the third and fourth failure of one
        # window; the success in between has to have reset the counter.
        assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=2, LOGIN_ACCOUNT_WINDOW_SECONDS=3)
    def test_block_expires_with_its_window(self):
        assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt().status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt().status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Sleep the window the lock-out actually published rather than the
        # configured one, so the test cannot be flaky on a slow machine.
        time.sleep(LoginAttemptService().blocked_seconds(EMAIL) + 0.2)

        assert self.attempt(password=PASSWORD).status_code == status.HTTP_200_OK

    @throttle_settings(
        LOGIN_ACCOUNT_FAILURE_LIMIT=2, LOGIN_ACCOUNT_WINDOW_SECONDS=900
    )
    def test_a_sustained_attack_cannot_extend_the_block(self):
        service = LoginAttemptService()
        self.attempt()
        self.attempt()
        first_remaining = service.blocked_seconds(EMAIL)
        assert first_remaining > 0

        for _ in range(5):
            self.attempt()

        # Still blocked, but the window is the one the first failure started:
        # hammering the endpoint neither extends nor clears it.
        assert 0 < service.blocked_seconds(EMAIL) <= first_remaining
        assert self.attempt(password=PASSWORD).status_code == (
            status.HTTP_429_TOO_MANY_REQUESTS
        )

    @throttle_settings(LOGIN_IP_RATE="2/min", LOGIN_ACCOUNT_FAILURE_LIMIT=1000)
    def test_address_ceiling_is_counted_per_client(self):
        first = {"REMOTE_ADDR": "10.0.0.1"}
        assert self.attempt(**first).status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt(**first).status_code == status.HTTP_401_UNAUTHORIZED
        assert self.attempt(**first).status_code == status.HTTP_429_TOO_MANY_REQUESTS

        other = {"REMOTE_ADDR": "10.0.0.2"}
        assert self.attempt(**other).status_code == status.HTTP_401_UNAUTHORIZED

    @throttle_settings(LOGIN_IP_RATE="2/min", LOGIN_ACCOUNT_FAILURE_LIMIT=1000)
    def test_address_ceiling_ignores_a_spoofed_forwarded_for(self):
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        ).status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8")
        ).status_code == status.HTTP_401_UNAUTHORIZED
        # Both spent the 10.0.0.1 budget: the header bought the attacker nothing.
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="9.9.9.9")
        ).status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @throttle_settings(
        LOGIN_IP_RATE="2/min",
        LOGIN_ACCOUNT_FAILURE_LIMIT=1000,
        TRUST_X_FORWARDED_FOR=True,
    )
    def test_forwarded_for_is_used_when_the_deployment_trusts_it(self):
        # Every request below comes from the same socket address, so a
        # REMOTE_ADDR-keyed ceiling would refuse the third one.
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        ).status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8")
        ).status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        ).status_code == status.HTTP_401_UNAUTHORIZED

        # The 1.2.3.4 budget is spent, and 5.6.7.8 is untouched: the ceiling
        # follows the client, not the proxy in front of it.
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        ).status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert (
            self.attempt(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8")
        ).status_code == status.HTTP_401_UNAUTHORIZED

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=2)
    def test_no_credential_or_address_is_ever_stored(self):
        self.attempt()
        self.attempt()

        ident = LoginAttemptService().account_ident(EMAIL)
        stored = f"{cache._cache!r}{cache._expire_info!r}"  # locmem internals

        assert PASSWORD not in stored
        assert EMAIL not in stored
        assert ident in stored
        assert LoginAttemptService().blocked_seconds(EMAIL) > 0

    @throttle_settings(LOGIN_ACCOUNT_FAILURE_LIMIT=2)
    def test_disabled_accounts_are_unchanged_and_do_not_spend_the_budget(self):
        User.objects.filter(email=EMAIL).update(status=User.Status.DISABLED)

        response = self.attempt(password=PASSWORD)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "disabled" in response.data["detail"].lower()
        assert LoginAttemptService().is_blocked(EMAIL) is False


class RefreshThrottleTests(APITestCase):
    """POST /auth/refresh/: bounded churn without weakening rotation."""

    def setUp(self):
        cache.clear()
        create_company(self.client)
        test_helpers.login(self.client, EMAIL, PASSWORD)
        cache.clear()

    def refresh(self):
        return test_helpers.post_refresh(self.client)

    def mint_refresh(self):
        token = RefreshToken()
        token["user_id"] = str(User.objects.get(email=EMAIL).pk)
        return str(token)

    @throttle_settings()
    def test_legitimate_bursts_stay_within_the_limit(self):
        """Single-flight plus a few tabs must never look like abuse."""
        for _ in range(5):
            response = self.refresh()
            assert response.status_code == status.HTTP_200_OK
            assert "access" in response.data

    @throttle_settings(REFRESH_SESSION_RATE="3/min")
    def test_subject_budget_throttles_repeated_refresh(self):
        for _ in range(3):
            assert self.refresh().status_code == status.HTTP_200_OK

        response = self.refresh()

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert int(response["Retry-After"]) > 0

    @throttle_settings(REFRESH_IP_RATE="1000/min", REFRESH_SESSION_RATE="2/min")
    def test_rotation_does_not_reset_the_subject_budget(self):
        first = test_helpers.refresh_cookie_value(self.client)
        assert self.refresh().status_code == status.HTTP_200_OK
        second = test_helpers.refresh_cookie_value(self.client)
        assert second != first
        assert self.refresh().status_code == status.HTTP_200_OK
        rotated = test_helpers.refresh_cookie_value(self.client)
        assert rotated not in (first, second)

        # A brand new token (new jti) and the budget still holds, so a stolen
        # session cannot be rotated indefinitely.
        assert self.refresh().status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @throttle_settings()
    def test_reusing_a_rotated_token_is_still_rejected(self):
        old = test_helpers.refresh_cookie_value(self.client)
        assert self.refresh().status_code == status.HTTP_200_OK

        self.client.cookies[settings.REFRESH_COOKIE_NAME] = old
        response = self.refresh()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired refresh token." in response.data["detail"]

    @throttle_settings(REFRESH_IP_RATE="2/min", REFRESH_SESSION_RATE="1000/min")
    def test_address_ceiling_covers_invalid_and_missing_tokens(self):
        self.client.cookies[settings.REFRESH_COOKIE_NAME] = "not.a.token"
        assert self.refresh().status_code == status.HTTP_401_UNAUTHORIZED
        del self.client.cookies[settings.REFRESH_COOKIE_NAME]
        assert self.refresh().status_code == status.HTTP_401_UNAUTHORIZED
        assert self.refresh().status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @throttle_settings(REFRESH_IP_RATE="1000/min", REFRESH_SESSION_RATE="2/min")
    def test_forged_token_cannot_spend_another_account_budget(self):
        assert self.refresh().status_code == status.HTTP_200_OK

        # Same payload, so it still claims this account, but a broken signature.
        # It must be rejected on its own merits, not by spending the verified
        # subject's budget: an attacker could otherwise lock a victim out by
        # replaying a mangled copy of their own token.
        real = test_helpers.refresh_cookie_value(self.client)
        head, payload, signature = real.split(".")
        forged = f"{head}.{payload}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
        self.client.cookies[settings.REFRESH_COOKIE_NAME] = forged
        assert self.refresh().status_code == status.HTTP_401_UNAUTHORIZED

        # Second legitimate refresh still succeeds, so the forged attempt cost
        # the subject budget nothing.
        self.client.cookies[settings.REFRESH_COOKIE_NAME] = real
        assert self.refresh().status_code == status.HTTP_200_OK

        # And the budget is real: the third legitimate refresh is refused.
        assert self.refresh().status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @throttle_settings(REFRESH_SESSION_RATE="2/min")
    def test_subject_history_expires_with_its_window(self):
        request = drf_request("/api/v1/auth/refresh/")
        request.COOKIES[settings.REFRESH_COOKIE_NAME] = self.mint_refresh()
        throttle = RefreshSubjectThrottle()

        assert throttle.allow_request(request, None) is True
        assert throttle.allow_request(request, None) is True
        assert throttle.allow_request(request, None) is False

        with mock.patch.object(
            RefreshSubjectThrottle, "timer", return_value=time.time() + 61
        ):
            assert throttle.allow_request(request, None) is True

    @throttle_settings(LOGIN_IP_RATE="1/min", REFRESH_IP_RATE="1000/min")
    def test_login_and_refresh_budgets_are_independent(self):
        login_url = reverse("auth-login")
        for _ in range(2):
            self.client.post(
                login_url, {"email": EMAIL, "password": "wrong"}, format="json"
            )

        assert self.refresh().status_code == status.HTTP_200_OK


class CacheFailureTests(APITestCase):
    """A cache outage must not turn into an outage of its own."""

    def setUp(self):
        cache.clear()
        create_company(self.client)
        self.broken_cache = mock.Mock()
        for operation in ("get", "set", "add", "delete", "incr", "touch"):
            getattr(self.broken_cache, operation).side_effect = RuntimeError(
                "cache down"
            )

    def broken(self):
        return mock.patch.multiple(
            "apps.accounts.services",
            cache=self.broken_cache,
            _cache_failure_reported=False,
        )

    def test_login_still_works_when_the_cache_is_unavailable(self):
        with self.broken(), self.assertLogs(
            "cetrak.security.auth", level="WARNING"
        ) as logs:
            response = self.client.post(
                reverse("auth-login"),
                {"email": EMAIL, "password": PASSWORD},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert any("degraded" in message for message in logs.output)

    def test_wrong_password_still_fails_cleanly_without_the_cache(self):
        with self.broken():
            response = self.client.post(
                reverse("auth-login"),
                {"email": EMAIL, "password": "wrong"},
                format="json",
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_cache_outage_is_reported_once_per_process(self):
        with self.broken(), self.assertLogs(
            "cetrak.security.auth", level="WARNING"
        ) as logs:
            for _ in range(3):
                self.client.post(
                    reverse("auth-login"),
                    {"email": EMAIL, "password": "wrong"},
                    format="json",
                )

        assert len([m for m in logs.output if m.startswith("WARNING")]) == 1

    def test_refresh_still_works_when_the_cache_is_unavailable(self):
        test_helpers.login(self.client, EMAIL, PASSWORD)

        with self.broken():
            response = test_helpers.post_refresh(self.client)

        assert response.status_code == status.HTTP_200_OK


class ThrottleKeyTests(SimpleTestCase):
    """Key derivation stays opaque, proxy-aware and endpoint-scoped."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_account_ident_is_stable_opaque_and_case_insensitive(self):
        service = LoginAttemptService()

        ident = service.account_ident("  User@Example.COM ")

        assert ident == service.account_ident("user@example.com")
        assert EMAIL not in ident
        assert len(ident) >= 32
        assert set(ident) <= set("0123456789abcdef")

    def test_forwarded_for_is_ignored_unless_the_deployment_trusts_it(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4"
        )
        with throttle_settings():
            assert client_ident(request) == "10.0.0.1"
        with throttle_settings(TRUST_X_FORWARDED_FOR=True):
            assert client_ident(request) == "1.2.3.4"

    def test_forwarded_for_chain_uses_the_originating_client(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="10.0.0.9", HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8"
        )
        with throttle_settings(TRUST_X_FORWARDED_FOR=True):
            assert client_ident(request) == "1.2.3.4"

    def test_client_ident_falls_back_when_no_address_is_present(self):
        request = self.factory.get("/")
        request.META.pop("REMOTE_ADDR", None)
        with throttle_settings():
            assert client_ident(request) == "unknown"

    def test_every_scope_uses_its_own_cache_namespace(self):
        login_request = drf_request(REMOTE_ADDR="10.0.0.1")
        refresh_request = drf_request("/api/v1/auth/refresh/", REMOTE_ADDR="10.0.0.1")
        refresh_request.COOKIES[settings.REFRESH_COOKIE_NAME] = "not.a.token"

        with throttle_settings():
            keys = {
                throttle.scope: throttle.get_cache_key(request, None)
                for throttle, request in (
                    (LoginAddressThrottle(), login_request),
                    (RefreshAddressThrottle(), refresh_request),
                    (RefreshSubjectThrottle(), refresh_request),
                )
            }

        assert len(set(keys.values())) == len(keys)
        assert all(key.startswith("throttle_") for key in keys.values())

    def test_throttles_are_inert_while_disabled(self):
        request = drf_request(data={"email": EMAIL, "password": "x"})

        assert throttle_enabled() is False
        assert LoginAddressThrottle().get_cache_key(request, None) is None
        assert RefreshSubjectThrottle().get_cache_key(request, None) is None
        assert LoginAccountThrottle().allow_request(request, None) is True


@contextmanager
def production_settings(redis_url=None, **extra_env):
    """Import ``config.settings.prod`` with a complete, throwaway environment.

    Every variable ``prod`` reads for the assertions below is pinned here rather
    than inherited, so the result cannot depend on what happens to be exported in
    the developer's shell — ``REDIS_URL`` in particular is always set explicitly
    (or explicitly absent), since the documented local ``.env`` exports one.
    """
    env = {
        "DJANGO_SECRET_KEY": "prod-test-secret-key",
        "DATABASE_URL": "sqlite:///:memory:",
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DJANGO_CSP_CONNECT_SRC": "",
        "CORS_ALLOWED_ORIGINS": "https://example.com",
        "CSRF_TRUSTED_ORIGINS": "https://example.com",
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_HOST_USER": "apikey",
        "EMAIL_HOST_PASSWORD": "supersecretvalue",
        "EMAIL_USE_TLS": "false",
        "EMAIL_USE_SSL": "false",
        "DEFAULT_FROM_EMAIL": "Cetrak <noreply@example.com>",
        "FRONTEND_URL": "https://app.example.com",
        **extra_env,
    }
    if redis_url is not None:
        env["REDIS_URL"] = redis_url
    names = ("config.settings.base", "config.settings.prod")
    previous_modules = {name: sys.modules.pop(name, None) for name in names}
    previous_env = {key: os.environ.get(key) for key in set(env) | {"REDIS_URL"}}
    os.environ.update(env)
    if redis_url is None:
        os.environ.pop("REDIS_URL", None)
    try:
        yield importlib.import_module("config.settings.prod")
    finally:
        for name, module in previous_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class ProductionThrottleSettingsTests(SimpleTestCase):
    """AUD-014: production must not run per-process throttle counters silently."""

    def test_shared_cache_is_used_when_redis_url_is_configured(self):
        url = "redis://cache.internal:6379/1"
        with production_settings(redis_url=url) as prod:
            assert prod.CACHES["default"]["BACKEND"] == (
                "django.core.cache.backends.redis.RedisCache"
            )
            assert prod.CACHES["default"]["LOCATION"] == url

    def test_missing_redis_url_warns_loudly_instead_of_failing_boots(self):
        with self.assertLogs("cetrak.security", level="WARNING") as logs:
            with production_settings() as prod:
                assert prod.CACHES["default"]["BACKEND"] == (
                    "django.core.cache.backends.locmem.LocMemCache"
                )

        assert any("process-local" in message for message in logs.output)

    def test_production_trusts_the_edge_proxy_forwarded_for(self):
        with production_settings() as prod:
            assert prod.AUTH_THROTTLE["TRUST_X_FORWARDED_FOR"] is True
