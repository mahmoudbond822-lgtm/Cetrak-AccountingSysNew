"""Opt-in throttle-state checks against a real Redis (AUD-014).

Everything about the throttle is covered hermetically against the in-process
cache in ``test_auth_throttling.py``. These tests exist for the one property
that depends on the *backend* rather than on our code: the login failure budget
relies on ``incr`` not re-arming the window TTL, which is what keeps a lock-out
bounded in time. LocMem and Redis both preserve it, but only a real Redis proves
it for the cache production actually uses.

Run with a Redis available and::

    CETRAK_REDIS_INTEGRATION=1 REDIS_URL=redis://localhost:6379/1 py -m pytest
"""

import os
import time
import uuid

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from apps.accounts.services import LoginAttemptService, auth_throttle_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("CETRAK_REDIS_INTEGRATION") != "1",
    reason="Real Redis round-trip only runs with CETRAK_REDIS_INTEGRATION=1.",
)

REDIS_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    }
}


@override_settings(CACHES=REDIS_CACHE)
class RedisThrottleStateTests(SimpleTestCase):
    """No ``cache.clear()`` anywhere: on Redis that is a FLUSHDB of the whole
    cache database, and these tests are pointed at a developer's own Redis.
    Every key written here is unique to the test, so it expires on its own."""

    def test_the_override_really_points_at_a_redis_client(self):
        # ``cache`` is a ConnectionProxy, so check the configured backend and the
        # client behind it. A LocMem cache would pass the behavioural tests below
        # while proving nothing about production, so this is asserted explicitly.
        assert settings.CACHES["default"]["BACKEND"] == (
            "django.core.cache.backends.redis.RedisCache"
        )
        assert "redis" in type(cache._cache).__module__

    def test_add_is_create_only_and_increment_is_atomic(self):
        key = f"audit014:probe:{uuid.uuid4()}"

        assert cache.add(key, 1, 60) is True
        assert cache.add(key, 1, 60) is False
        assert cache.incr(key) == 2
        assert cache.incr(key) == 3

    def test_increment_does_not_extend_the_window(self):
        """The property the bounded lock-out rests on.

        A two second key is incremented half way through its life. If ``incr``
        re-armed the expiry (as the generic base-cache implementation would) the
        key would still be there afterwards.
        """
        key = f"audit014:probe:{uuid.uuid4()}"
        cache.add(key, 1, 2)

        time.sleep(1.1)
        assert cache.incr(key) == 2
        time.sleep(1.1)

        assert cache.get(key) is None

    def test_login_budget_behaves_the_same_on_redis(self):
        service = LoginAttemptService()
        email = f"probe-{uuid.uuid4()}@example.com"
        with override_settings(
            AUTH_THROTTLE=dict(auth_throttle_settings(), LOGIN_ACCOUNT_FAILURE_LIMIT=3)
        ):
            service.record_failure(email)
            service.record_failure(email)
            assert service.blocked_seconds(email) == 0

            service.record_failure(email)
            remaining = service.blocked_seconds(email)
            assert 0 < remaining <= 900

            for _ in range(5):
                service.record_failure(email)
            assert service.blocked_seconds(email) <= remaining

            service.record_success(email)
            assert service.is_blocked(email) is False
