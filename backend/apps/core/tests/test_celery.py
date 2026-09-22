import importlib
import os
import uuid
from urllib.parse import urlparse

import pytest
from django.conf import settings

from config.celery import app as celery_app

from apps.core.tasks import ping

_BASE_DEFAULT_BROKER = "redis://localhost:6379/0"


class TestCeleryApplication:
    def test_app_imports_and_is_named_cetrak(self):
        assert celery_app.main == "cetrak"

    def test_config_comes_from_django_settings(self):
        assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL

    def test_broker_and_result_settings_are_set(self):
        assert settings.CELERY_BROKER_URL
        assert settings.CELERY_RESULT_BACKEND
        assert celery_app.conf.broker_url
        assert celery_app.conf.result_backend

    def test_broker_and_result_are_env_driven(self):
        expected = os.environ.get("CELERY_BROKER_URL", _BASE_DEFAULT_BROKER)
        assert settings.CELERY_BROKER_URL == expected
        assert settings.CELERY_RESULT_BACKEND == os.environ.get(
            "CELERY_RESULT_BACKEND", _BASE_DEFAULT_BROKER
        )

    def test_broker_and_result_urls_have_no_embedded_credentials(self):
        for url in (settings.CELERY_BROKER_URL, settings.CELERY_RESULT_BACKEND):
            parsed = urlparse(url)
            assert parsed.scheme == "redis"
            assert parsed.password is None


class TestCelerySerialization:
    def test_task_serializer_is_json(self):
        assert settings.CELERY_TASK_SERIALIZER == "json"

    def test_result_serializer_is_json(self):
        assert settings.CELERY_RESULT_SERIALIZER == "json"

    def test_only_json_accepted_content(self):
        assert settings.CELERY_ACCEPT_CONTENT == ["json"]
        assert "pickle" not in settings.CELERY_ACCEPT_CONTENT


class TestCeleryTimezone:
    def test_worker_timezone_matches_django(self):
        assert settings.CELERY_TIMEZONE == settings.TIME_ZONE
        assert settings.CELERY_TIMEZONE == "UTC"

    def test_utc_is_enabled(self):
        assert settings.CELERY_ENABLE_UTC is True


class TestCeleryBrokerStartup:
    def test_broker_retry_on_startup_enabled(self):
        assert settings.CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP is True


class TestCeleryDiscovery:
    def test_infrastructure_task_is_registered(self):
        assert "core.ping" in celery_app.tasks

    def test_autodiscovered_modules_import_cleanly(self):
        for module in celery_app.loader.import_default_modules():
            assert module is not None


class TestCeleryExecution:
    def test_ping_executes_and_returns_payload(self):
        result = ping.delay(message="hello")
        payload = result.get()
        assert payload["message"] == "hello"
        assert payload["task_id"]

    def test_ping_is_idempotent_pure_function(self):
        first = ping.delay(message="same")
        second = ping.delay(message="same")
        assert first.get()["message"] == "same"
        assert second.get()["message"] == "same"
        assert first.get()["task_id"] != second.get()["task_id"]

    def test_ping_roundtrips_via_apply_async(self):
        payload = ping.apply_async(kwargs={"message": "roundtrip"}).get()
        assert payload["message"] == "roundtrip"
        assert uuid.UUID(payload["task_id"])

    def test_eager_mode_executes_inline_in_tests(self):
        assert settings.CELERY_TASK_ALWAYS_EAGER is True

    def test_eager_mode_propagates_exceptions(self):
        from config.celery import app

        @app.task(name="test.failing.task")
        def failing_task():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            failing_task.delay()


class TestEagerDoesNotLeakToProduction:
    def test_base_settings_do_not_enable_eager_mode(self):
        base = importlib.import_module("config.settings.base")
        assert not getattr(base, "CELERY_TASK_ALWAYS_EAGER", False)
        assert not getattr(base, "CELERY_TASK_EAGER_PROPAGATES", False)