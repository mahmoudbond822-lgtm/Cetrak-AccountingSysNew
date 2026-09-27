import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

# The variables that together select a real PostgreSQL server. All four are
# required: a partial set is a misconfiguration, not a request for SQLite.
_POSTGRES_ENV = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST")


def _sqlite_config():
    """A *fresh* in-memory SQLite config.

    Built per call rather than shared as a module constant on purpose: Django's
    test runner mutates ``settings.DATABASES`` in place while creating the test
    database, rewriting ``NAME`` to ``file:memorydb_default?mode=memory
    &cache=shared``. A shared dict would be corrupted for every later caller of
    this function for the rest of the process.
    """
    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }


def _database_config(env):
    """Resolve the test database backend from *env*.

    ``CETRAK_TEST_DB`` makes the choice explicit:

    ``postgres``
        use PostgreSQL, and raise if the connection details are incomplete.
        A CI job that means to test PostgreSQL must never quietly end up on
        SQLite: ``apps/accounting/migrations/0005`` installs a CHECK
        constraint that SQLite ignores, so a silent fallback turns the suite
        green while skipping the behaviour it exists to verify.
    ``sqlite``
        use in-memory SQLite even when ``POSTGRES_*`` is present, so the fast
        local job is immune to an ambient environment.
    unset (the default)
        keep the historical inference: all four ``POSTGRES_*`` variables set
        means PostgreSQL, anything less means SQLite. This is what every
        existing local invocation already relies on.
    """
    requested = env.get("CETRAK_TEST_DB", "").strip().lower()
    if requested not in ("", "postgres", "sqlite"):
        raise ImproperlyConfigured(
            f"CETRAK_TEST_DB must be 'postgres' or 'sqlite', not {requested!r}."
        )

    missing = [name for name in _POSTGRES_ENV if not env.get(name)]
    if requested == "sqlite":
        return _sqlite_config()
    if requested == "postgres" and missing:
        raise ImproperlyConfigured(
            "CETRAK_TEST_DB=postgres requires "
            + ", ".join(missing)
            + " to be set; refusing to fall back to SQLite, because a suite that "
            "silently skips the database-specific migrations is not a pass."
        )
    if missing:
        return _sqlite_config()

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env["POSTGRES_DB"],
            "USER": env["POSTGRES_USER"],
            "PASSWORD": env["POSTGRES_PASSWORD"],
            "HOST": env["POSTGRES_HOST"],
            "PORT": env.get("POSTGRES_PORT", "5432"),
        }
    }


DATABASES = _database_config(os.environ)

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

# AUD-014: the login/refresh throttles are attached to those endpoints and stay
# enabled in every other environment, so they are switched off here to keep the
# rest of the suite behaving exactly as before. apps/accounts/tests/
# test_auth_throttling.py re-enables them with override_settings and exercises
# the real limits (and deliberately tightened ones).
AUTH_THROTTLE = dict(AUTH_THROTTLE, ENABLED=False)

# The throttle state must never depend on an external cache in tests.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
