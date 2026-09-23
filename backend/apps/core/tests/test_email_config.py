import importlib
import os
import sys

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_PROD_REQUIRED = ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
                  "DEFAULT_FROM_EMAIL", "FRONTEND_URL")


def _prod_env(overrides=None, drop=None):
    values = {
        "DJANGO_SECRET_KEY": "prod-secret-not-default",
        "DJANGO_ALLOWED_HOSTS": "api.example.com",
        "DATABASE_URL": "postgres://u:p@localhost:5432/cetrak",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
        "CSRF_TRUSTED_ORIGINS": "https://app.example.com",
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_HOST_USER": "apikey",
        "EMAIL_HOST_PASSWORD": "supersecretvalue",
        "DEFAULT_FROM_EMAIL": "Cetrak <noreply@example.com>",
        "EMAIL_USE_TLS": "true",
        "EMAIL_USE_SSL": "false",
        "FRONTEND_URL": "https://app.example.com",
    }
    values.update(overrides or {})
    for key in drop or []:
        values.pop(key, None)
    return values


def _load_prod(monkeypatch, env_values):
    # prod.py derives EMAIL_*/SECRET_KEY/FRONTEND_URL from the base module via
    # `from .base import *`, so mirror the env onto the base module attributes.
    # Resolve the base module at call time: a prior test may have re-imported it,
    # and prod must star-import the same object we are patching.
    base = importlib.import_module("config.settings.base")
    monkeypatch.setattr(base, "SECRET_KEY",
                        env_values.get("DJANGO_SECRET_KEY", base.SECRET_KEY))
    monkeypatch.setattr(base, "EMAIL_BACKEND", env_values["EMAIL_BACKEND"])
    monkeypatch.setattr(base, "EMAIL_USE_TLS",
                        env_values.get("EMAIL_USE_TLS", "false").lower() == "true")
    monkeypatch.setattr(base, "EMAIL_USE_SSL",
                        env_values.get("EMAIL_USE_SSL", "false").lower() == "true")
    for name in _PROD_REQUIRED:
        monkeypatch.setattr(base, name, env_values.get(name, ""))
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)
    for key in list(os.environ):
        if (key.startswith("EMAIL_") or key in ("FRONTEND_URL", "DEFAULT_FROM_EMAIL")) \
                and key not in env_values:
            monkeypatch.delenv(key, raising=False)
    # prod's `INSTALLED_APPS += [...]` mutates the shared base list in place;
    # hand prod a disposable copy so the active settings stay untouched.
    monkeypatch.setattr(base, "INSTALLED_APPS", list(base.INSTALLED_APPS))
    sys.modules.pop("config.settings.prod", None)
    return importlib.import_module("config.settings.prod")


class TestEmailConfigDefaults:
    def test_base_defaults_to_console_backend(self):
        base = importlib.import_module("config.settings.base")
        expected = os.environ.get(
            "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
        )
        assert base.EMAIL_BACKEND == expected

    def test_test_settings_use_locmem_backend(self):
        assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"

    def test_base_default_frontend_url_is_local_dev(self):
        base = importlib.import_module("config.settings.base")
        assert base.FRONTEND_URL == os.environ.get("FRONTEND_URL", "http://localhost:3000")

    def test_test_settings_still_eager(self):
        assert settings.CELERY_TASK_ALWAYS_EAGER is True


class TestProdEmailConfig:
    def test_prod_imports_cleanly_with_full_email_config(self, monkeypatch):
        prod = _load_prod(monkeypatch, _prod_env())
        assert prod.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
        assert prod.EMAIL_HOST == "smtp.example.com"
        assert prod.FRONTEND_URL == "https://app.example.com"

    @pytest.mark.parametrize("backend", [
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    ])
    def test_prod_rejects_development_backends(self, monkeypatch, backend):
        with pytest.raises(ImproperlyConfigured) as exc_info:
            _load_prod(monkeypatch, _prod_env(overrides={"EMAIL_BACKEND": backend}))
        assert "EMAIL_BACKEND" in str(exc_info.value)
        assert "core.mail.backends.smtp" in str(exc_info.value)

    @pytest.mark.parametrize("missing", list(_PROD_REQUIRED))
    def test_prod_fails_when_required_email_var_missing(self, monkeypatch, missing):
        with pytest.raises(ImproperlyConfigured) as exc_info:
            _load_prod(monkeypatch, _prod_env(drop=[missing]))
        assert missing in str(exc_info.value)
        assert "must be set in production" in str(exc_info.value)

    def test_prod_requires_explicit_fallback_free_config(self, monkeypatch):
        with pytest.raises(ImproperlyConfigured) as exc_info:
            _load_prod(monkeypatch, _prod_env(drop=["EMAIL_HOST"]))
        assert "EMAIL_HOST" in str(exc_info.value)

    def test_prod_rejects_tls_and_ssl_together(self, monkeypatch):
        with pytest.raises(ImproperlyConfigured) as exc_info:
            _load_prod(
                monkeypatch,
                _prod_env(overrides={"EMAIL_USE_TLS": "true", "EMAIL_USE_SSL": "true"}),
            )
        assert "mutually exclusive" in str(exc_info.value)

    def test_prod_error_never_exposes_secret_value(self, monkeypatch):
        secret = "supersecretvalue"
        with pytest.raises(ImproperlyConfigured) as exc_info:
            _load_prod(monkeypatch, _prod_env(drop=["EMAIL_HOST_PASSWORD"]))
        assert secret not in str(exc_info.value)