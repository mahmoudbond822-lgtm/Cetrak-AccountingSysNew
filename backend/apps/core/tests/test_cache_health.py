"""B2: the health endpoint must not claim a shared cache it does not have.

The old probe set and read a key in ``django.core.cache.cache`` and reported
``cache: ok``. LocMem answers that perfectly, so a production deployment with no
``REDIS_URL`` reported a healthy cache while every gunicorn worker kept its own
AUD-014 throttle counters — the failure the probe existed to catch. The value
reported now comes from the configured backend as well as the probe.

The "unavailable Redis" case is exercised against a Redis URL nothing listens on,
so it needs no server; the healthy case against a real Redis is opt-in with
``CETRAK_REDIS_INTEGRATION=1``, matching the existing throttle integration tests.
"""

import os

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings


from apps.core.health import cache_backend, check_cache, uses_shared_cache

# Nothing listens here: 127.0.0.1/1 is not a routable service port.
UNREACHABLE_REDIS = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:1/1",
        "OPTIONS": {"socket_connect_timeout": 1, "socket_timeout": 1},
    }
}

REDIS_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    }
}

LOCMEM_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}

requires_real_redis = pytest.mark.skipif(
    os.environ.get("CETRAK_REDIS_INTEGRATION") != "1",
    reason="Real Redis round-trip only runs with CETRAK_REDIS_INTEGRATION=1.",
)


class TestCacheBackendDetection(SimpleTestCase):
    def test_test_environment_uses_locmem_and_does_not_require_sharing(self):
        assert cache_backend() == "django.core.cache.backends.locmem.LocMemCache"
        assert uses_shared_cache() is False
        assert settings.CACHE_MUST_BE_SHARED is False

    @override_settings(CACHES=REDIS_CACHE)
    def test_redis_backend_counts_as_shared(self):
        assert uses_shared_cache() is True


class TestCacheProbe(SimpleTestCase):
    """The value the endpoint reports, per configuration."""

    def test_healthy_test_cache_reports_ok(self):
        """Nothing about a healthy single-process cache changed."""
        assert check_cache() == (True, "ok")

    @override_settings(CACHES=LOCMEM_CACHE, CACHE_MUST_BE_SHARED=True)
    def test_process_local_cache_is_never_reported_healthy(self):
        assert check_cache() == (False, "process_local")


@override_settings(CACHES=UNREACHABLE_REDIS, CACHE_MUST_BE_SHARED=True)
class TestUnreachableRedis(SimpleTestCase):
    def test_unreachable_redis_is_reported_unreachable(self):
        assert check_cache() == (False, "unreachable")


class TestHealthEndpoint(TestCase):
    """The endpoint itself, through the URL the Render health check polls.

    ``TestCase`` rather than ``SimpleTestCase``: the view opens a database
    connection to report the ``database`` field.
    """

    def test_health_endpoint_reports_ok_for_a_healthy_cache(self):
        response = self.client.get("/api/v1/health/")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["cache"] == "ok"
        assert payload["database"] == "ok"

    @override_settings(CACHES=LOCMEM_CACHE, CACHE_MUST_BE_SHARED=True)
    def test_process_local_cache_degrades_the_endpoint(self):
        response = self.client.get("/api/v1/health/")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["database"] == "ok", "only the cache is at fault here"
        assert payload["cache"] == "process_local"

    @override_settings(CACHES=UNREACHABLE_REDIS, CACHE_MUST_BE_SHARED=True)
    def test_unreachable_redis_degrades_the_endpoint(self):
        response = self.client.get("/api/v1/health/")

        assert response.json()["status"] == "degraded"
        assert response.json()["cache"] == "unreachable"


@requires_real_redis
@override_settings(CACHES=REDIS_CACHE, CACHE_MUST_BE_SHARED=True)
class TestRealRedis(SimpleTestCase):
    def test_the_override_really_points_at_a_redis_client(self):
        # ``cache`` is a ConnectionProxy, so the configured backend is not proof
        # on its own: assert the client behind it too. A silent LocMem fallback
        # would make the probe assertions below pass while proving nothing.
        assert "redis" in type(cache._cache).__module__

    def test_healthy_redis_is_reported_ok(self):
        assert check_cache() == (True, "ok")

    def test_health_endpoint_reports_ok(self):
        assert self.client.get("/api/v1/health/").json()["cache"] == "ok"
