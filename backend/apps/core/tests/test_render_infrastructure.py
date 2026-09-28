"""The deployment manifest has to actually produce the B1/B2 configuration.

These tests read ``render.yaml`` as data and assert the wiring a Render sync
would create: a Key Value instance, the Celery worker service, the Redis and
Celery URLs resolved from that instance on both the web service and the worker,
and one shared secret. They are the regression net for a manifest that parses but
does not deploy — the failure mode that left production falling back to
``redis://localhost:6379/0`` with no worker to consume anything.

The manifest is also validated against Render's published JSON schema here, so a
field that Render does not accept fails the suite rather than the deploy.
"""

import importlib
import json
import urllib.request
from pathlib import Path

import pytest

from apps.core.tests.test_email_config import _load_prod, _prod_env

REPO_ROOT = Path(__file__).resolve().parents[4]
RENDER_YAML = REPO_ROOT / "render.yaml"
RENDER_SCHEMA_URL = "https://render.com/schema/render.yaml.json"

REDIS_SERVICE = "cetrak-redis"
WEB_SERVICE = "cetrak-api"
WORKER_SERVICE = "cetrak-worker"
# Render's Key Value connectionString is redis://[user:password@]red-xxxx:6379
# over the private network; the value itself is created by Render.
REDIS_ENV_VARS = ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND")
# What config.settings.prod refuses to boot without.
PROD_REQUIRED_ENV_VARS = (
    "DJANGO_SETTINGS_MODULE",
    "DATABASE_URL",
    "FRONTEND_URL",
    "EMAIL_BACKEND",
    "EMAIL_HOST",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "DEFAULT_FROM_EMAIL",
)


@pytest.fixture(scope="module")
def manifest():
    yaml = pytest.importorskip("yaml", reason="PyYAML is needed to read render.yaml")
    return yaml.safe_load(RENDER_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema():
    """Render's own blueprint schema, or skip if it cannot be fetched.

    ``jsonschema`` is a declared test dependency (requirements/dev.txt); the
    schema itself is fetched from Render at run time, so this fixture only
    skips when the network fetch fails, e.g. when running offline.
    """
    jsonschema = pytest.importorskip("jsonschema")
    cached = getattr(TestRenderManifest, "_schema_cache", None)
    if cached is None:
        try:
            with urllib.request.urlopen(RENDER_SCHEMA_URL, timeout=15) as response:
                cached = json.loads(response.read().decode("utf-8"))
        except OSError as exc:  # offline: every other assertion still runs
            pytest.skip(f"Render blueprint schema unavailable: {exc}")
        TestRenderManifest._schema_cache = cached
    return cached


def service(manifest, name):
    for entry in manifest["services"]:
        if entry["name"] == name:
            return entry
    raise AssertionError(f"service {name!r} is missing from render.yaml")


def env_map(entry):
    """``key -> definition`` for a service's own environment variables."""
    return {
        item["key"]: item for item in entry.get("envVars", []) if "key" in item
    }


class TestRenderManifest:
    def test_manifest_matches_the_published_render_schema(self, manifest, schema):
        # The fixture already skipped if jsonschema is unavailable.
        jsonschema = pytest.importorskip("jsonschema")
        jsonschema.validate(instance=manifest, schema=schema)

    def test_key_value_instance_exists_for_cache_and_broker(self, manifest):
        redis_service = service(manifest, REDIS_SERVICE)

        assert redis_service["type"] == "keyvalue"
        # ipAllowList is required for Key Value; empty means private-network only.
        assert redis_service["ipAllowList"] == []
        assert redis_service["maxmemoryPolicy"] == "noeviction"

    @pytest.mark.parametrize("service_name", [WEB_SERVICE, WORKER_SERVICE])
    def test_redis_and_celery_come_from_the_key_value_instance(self, manifest, service_name):
        variables = env_map(service(manifest, service_name))

        for key in REDIS_ENV_VARS:
            assert variables[key]["fromService"] == {
                "type": "keyvalue",
                "name": REDIS_SERVICE,
                "property": "connectionString",
            }, f"{service_name} must resolve {key} from {REDIS_SERVICE}"

    def test_worker_service_runs_the_existing_celery_application(self, manifest):
        worker = service(manifest, WORKER_SERVICE)

        assert worker["type"] == "worker"
        assert worker["runtime"] == "python"
        assert worker["rootDir"] == "backend"
        # `celery -A config` is config/celery.py's app: no second entry point.
        assert worker["startCommand"] == "celery -A config worker -l info"
        assert worker["envVars"][0] == {
            "key": "DJANGO_SETTINGS_MODULE",
            "value": "config.settings.prod",
        }
        # Migrations belong to the web service's build, not to every deploy.
        assert "migrate" not in worker["buildCommand"]

    @pytest.mark.parametrize("service_name", [WEB_SERVICE, WORKER_SERVICE])
    def test_every_production_requirement_reaches_the_service(self, manifest, service_name):
        variables = env_map(service(manifest, service_name))

        for key in PROD_REQUIRED_ENV_VARS:
            assert key in variables, f"{service_name} is missing {key}"
        assert variables["DATABASE_URL"]["fromDatabase"] == {
            "name": "cetrak-db",
            "property": "connectionString",
        }

    def test_email_credentials_are_prompted_not_committed(self, manifest):
        for service_name in (WEB_SERVICE, WORKER_SERVICE):
            variables = env_map(service(manifest, service_name))
            for key in ("EMAIL_HOST_PASSWORD", "EMAIL_HOST_USER", "FRONTEND_URL"):
                assert variables[key] == {"key": key, "sync": False}

    def test_web_and_worker_share_one_secret_key(self, manifest):
        groups = {group["name"]: group["envVars"] for group in manifest["envVarGroups"]}
        assert len(groups) == 1
        (group_name, group_vars) = next(iter(groups.items()))
        assert [item["key"] for item in group_vars] == ["DJANGO_SECRET_KEY"]
        assert group_vars[0]["generateValue"] is True

        for service_name in (WEB_SERVICE, WORKER_SERVICE):
            entry = service(manifest, service_name)
            from_groups = [item["fromGroup"] for item in entry["envVars"] if "fromGroup" in item]
            assert from_groups == [group_name]
            # A per-service generateValue would hand the two processes
            # different signing material.
            assert not [item for item in entry["envVars"] if "generateValue" in item]

    def test_no_secret_or_connection_string_is_hard_coded(self, manifest):
        allowed_values = {
            ("cetrak-api", "DJANGO_SETTINGS_MODULE"),
            ("cetrak-api", "DJANGO_ALLOWED_HOSTS"),
            ("cetrak-worker", "DJANGO_SETTINGS_MODULE"),
            ("cetrak-worker", "DJANGO_ALLOWED_HOSTS"),
        }
        hard_coded = [
            (entry["name"], item["key"], item["value"])
            for entry in manifest["services"]
            for item in entry.get("envVars", [])
            if "value" in item and (entry["name"], item["key"]) not in allowed_values
        ]
        for database in manifest["databases"]:
            hard_coded += [
                (database["name"], key, value)
                for key, value in database.items()
                if key in ("password", "connectionString")
            ]

        assert hard_coded == []


class TestProductionSettingsReadTheBrokerAndCache:
    """prod.py must turn the manifest's environment into the runtime config."""

    def test_redis_url_configures_the_shared_cache(self, monkeypatch):
        prod = _load_prod(
            monkeypatch, _prod_env(overrides={"REDIS_URL": "redis://red-example:6379/0"})
        )

        assert prod.CACHES["default"]["BACKEND"] == (
            "django.core.cache.backends.redis.RedisCache"
        )
        assert prod.CACHES["default"]["LOCATION"] == "redis://red-example:6379/0"
        assert prod.CACHE_MUST_BE_SHARED is True

    def test_broker_urls_reach_the_celery_configuration(self, monkeypatch):
        prod = _load_prod(
            monkeypatch,
            _prod_env(
                overrides={
                    "CELERY_BROKER_URL": "redis://red-example:6379/0",
                    "CELERY_RESULT_BACKEND": "redis://red-example:6379/0",
                }
            ),
        )

        assert prod.CELERY_BROKER_URL == "redis://red-example:6379/0"
        assert prod.CELERY_RESULT_BACKEND == "redis://red-example:6379/0"

        from config.celery import app as celery_app

        assert celery_app.conf.broker_url == prod.CELERY_BROKER_URL

    def test_missing_redis_url_falls_back_to_locmem_but_stays_flagged(self, monkeypatch):
        prod = _load_prod(monkeypatch, _prod_env(drop=["REDIS_URL"]))

        assert prod.CACHES["default"]["BACKEND"] == (
            "django.core.cache.backends.locmem.LocMemCache"
        )
        # The health check turns this exact situation into a degraded report.
        assert prod.CACHE_MUST_BE_SHARED is True

    def test_eager_mode_never_leaks_into_production(self, monkeypatch):
        base = importlib.import_module("config.settings.base")
        prod = _load_prod(monkeypatch, _prod_env())

        assert not getattr(base, "CELERY_TASK_ALWAYS_EAGER", False)
        assert not getattr(prod, "CELERY_TASK_ALWAYS_EAGER", False)
        assert not getattr(prod, "CELERY_TASK_EAGER_PROPAGATES", False)
