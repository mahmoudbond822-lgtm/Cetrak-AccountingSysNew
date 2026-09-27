"""Cache health probe for the deployment health endpoint (B2).

``/api/v1/health/`` is polled by Render and read by operators, so it must not
claim a healthy shared cache when the process is running on a per-process one.
A LocMem cache answers a set/get probe perfectly while the AUD-014 throttle
counters inside it are invisible to the other gunicorn workers, so every limit
is effectively multiplied by the worker count — the exact failure this probe
used to hide. The reported value is derived from the configured backend, not
only from the probe result.
"""

import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps.core.health")

# Backends whose state is shared by every process using the deployment. Only
# these count as "shared" for throttling purposes; LocMem and DatabaseCache
# behind a local file are per-process.
SHARED_CACHE_BACKENDS = frozenset(
    {
        "django.core.cache.backends.redis.RedisCache",
        "django.core.cache.backends.redis.RedisCacheCluster",
        "django_redis.cache.RedisCache",
    }
)


def cache_backend():
    """The dotted path configured for the default cache ('' if unusable)."""
    try:
        return settings.CACHES["default"]["BACKEND"]
    except (AttributeError, KeyError, TypeError):
        return ""


def uses_shared_cache():
    """True when every process on this deployment sees the same cache state."""
    return cache_backend() in SHARED_CACHE_BACKENDS


def _probe():
    try:
        cache.set("_health_check", "ok", timeout=5)
        return cache.get("_health_check") == "ok"
    except Exception:
        return False


def check_cache():
    """Return ``(healthy, reported_value)`` for the health payload.

    ``reported_value`` is one of:
      * ``ok``            — the configured cache answered a set/get. Shared
                            whenever the environment requires a shared cache.
      * ``unreachable``   — the configured cache did not answer.
      * ``process_local`` — a shared cache is required (production) but the
                            default cache is per-process. Never reported as ok.
    """
    if getattr(settings, "CACHE_MUST_BE_SHARED", False) and not uses_shared_cache():
        logger.error(
            "shared cache required but the default cache backend is %r: "
            "throttle state is not shared between workers",
            cache_backend(),
        )
        return False, "process_local"
    if not _probe():
        logger.warning("cache probe failed for backend %r", cache_backend())
        return False, "unreachable"
    return True, "ok"
