import logging
import os

import dj_database_url

from django.core.exceptions import ImproperlyConfigured

from .base import *

logger = logging.getLogger("cetrak.security")


def _csv_env(name):
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


DEBUG = False

if SECRET_KEY == "django-insecure-change-me-in-production":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable must be set in production."
    )

# Email delivery (AUD-015): production must never silently fall back to a
# development backend (console/locmem) or send from an unconfigured SMTP relay.
# Fail fast on missing or ambiguous configuration instead.
if EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
    raise ImproperlyConfigured(
        "EMAIL_BACKEND must be 'django.core.mail.backends.smtp.EmailBackend' "
        "in production; development backends are not permitted."
    )

for _name in ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
              "DEFAULT_FROM_EMAIL", "FRONTEND_URL"):
    if not os.environ.get(_name):
        raise ImproperlyConfigured(
            f"{_name} environment variable must be set in production."
        )

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured(
        "EMAIL_USE_TLS and EMAIL_USE_SSL are mutually exclusive; set only one "
        "in production."
    )

ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS")

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

INSTALLED_APPS += [
    "corsheaders",
]

MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"] + MIDDLEWARE
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
MIDDLEWARE.append("apps.core.middleware.SecurityHeadersMiddleware")

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = _csv_env("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _csv_env("CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(__import__("corsheaders.defaults", fromlist=["default_headers"]).default_headers) + [
    "x-csrf-token",
    "x-tenant-id",
]

REFRESH_COOKIE_SECURE = True

# --- Authentication throttling (AUD-014) ------------------------------------
# Throttle state must be shared: gunicorn runs several workers per instance and
# the service is expected to scale out, so per-process counters would multiply
# every limit by the number of workers/instances. REDIS_URL is the existing
# convention documented in backend/.env.example; locally it points at database 1
# while Celery uses database 0, and on Render all of REDIS_URL /
# CELERY_BROKER_URL / CELERY_RESULT_BACKEND are the same Key Value instance.
#
# CACHE_MUST_BE_SHARED is what makes the below a hard requirement rather than a
# preference: apps.core.health refuses to report the cache as healthy while the
# effective backend is process-local, so a deployment that lost REDIS_URL is
# visible on the endpoint Render already polls instead of looking fine.
CACHE_MUST_BE_SHARED = True

_cache_url = os.environ.get("REDIS_URL", "").strip()
if _cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_url,
        }
    }
else:
    # Not silent: without a shared cache the limits below only hold per
    # process, so say so loudly at boot rather than assuming protection.
    logger.warning(
        "REDIS_URL is not set: authentication throttling state is process-local "
        "and every limit is effectively multiplied by the number of web workers. "
        "Set REDIS_URL to a shared Redis instance."
    )
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# The web service is only reachable through the platform's edge proxy, which
# overwrites X-Forwarded-For, so the client address is taken from it. Without
# this every request would share the proxy's address.
AUTH_THROTTLE["TRUST_X_FORWARDED_FOR"] = True

_extra_connect_src = _csv_env("DJANGO_CSP_CONNECT_SRC")
if _extra_connect_src:
    CONTENT_SECURITY_POLICY = CONTENT_SECURITY_POLICY.replace(
        "connect-src 'self'",
        "connect-src 'self' " + " ".join(_extra_connect_src),
    )

STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
