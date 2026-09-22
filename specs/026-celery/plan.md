# Implementation Plan: AUD-026 — Celery Background Task Foundation

**Branch**: current | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

## Summary

Make the existing Celery scaffold production-safe and deterministic: move all Celery
configuration into `base.py` (env-driven Redis broker/result, JSON-only serialization,
UTC alignment), enable eager mode only in tests, register one idempotent
infrastructure proof task, document the broker convention, and prove it all with
unit tests plus an opt-in integration test — with zero changes to accounting, auth,
API, frontend, or deployment behavior.

## Current State (verified this session)

- Django `6.0.4`; Celery `5.6.3`; redis-py `7.4.0`; requirements pins already exist
  (`celery>=5.3,<6.0`, `redis>=7.0,<8.0`) — **no dependency change**.
- `config/celery.py` already defines the single standard app object
  (`config_from_object(..., namespace="CELERY")` + `autodiscover_tasks()`), exported by
  `config/__init__.py`. Under `config.settings.test`, `app.conf.broker_url` is `None`
  because only `dev.py` declares broker/result URLs.
- Compose already runs `redis:7-alpine` + a `worker` service (`celery -A config worker`,
  profile `worker`) with explicit `CELERY_*` env. `accounts/tasks.py` is an import-only
  re-export. Task count: **0**; no scheduling anywhere; no `.delay`/`apply_async` calls
  anywhere in the repo.

## Steps

### Step 1 — Deterministic Celery settings (`base.py`)

Append a Celery block to `backend/config/settings/base.py`:

```python
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

- Env-driven with a **local** default (no production host/credential hard-coded).
- JSON-only in/out and JSON-only accepted content: no pickle execution path from the
  broker or into the result backend.
- Worker timezone/UTC mirrors Django (`USE_TZ = True`, `TIME_ZONE = "UTC"`).
- Broker retry on startup: deterministic worker boot ordering (compose `depends_on`
  healthy redis) + removes the Celery 5.3+ deprecation warning.
- These settings now reach **prod** and **test** (which import `base.py`), closing the
  "`broker_url is None` under prod/test" gap.

### Step 2 — Remove redundant broker overrides (`dev.py`)

Delete the two `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` lines from
`backend/config/settings/dev.py`. They are superseded by `base.py` (same env vars, same
source of truth). Behavior is preserved: compose's `worker` service passes explicit
values; out-of-compose dev now correctly defaults to `localhost` instead of the
unresolvable compose hostname `redis`. No non-Celery dev settings change.

### Step 3 — Test-only eager mode (`test.py`)

Add to `backend/config/settings/test.py`:

```python
# Celery runs inline in tests so unit tests need no Redis/broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

- `ALWAYS_EAGER`: `.delay()` executes in-process → deterministic, no infrastructure.
- `EAGER_PROPAGATES`: task exceptions re-raise to the caller → failures are never
  swallowed and cannot become silent "always green" tasks.
- `test.py` is never imported by `prod.py`/`dev.py`, so eager cannot leak; Step 6
  asserts this on `base.py` explicitly.

### Step 4 — Infrastructure proof task (`apps/core/tasks.py`)

Create `backend/apps/core/tasks.py`:

```python
from config.celery import app as celery_app


@celery_app.task(name="core.ping")
def ping(message=None):
    """Infrastructure proof: exercises broker -> worker -> result backend."""
    return {"task_id": ping.request.id, "message": message}
```

- `apps.core` is already in `INSTALLED_APPS` → `autodiscover_tasks()` finds it.
- Idempotent pure function: no DB, no request/session, no credentials in args or logs,
  JSON-safe return payload, no internal exception swallowing.
- Proves the async pipeline executes and returns a result a test can assert on.

Delete `backend/apps/accounts/tasks.py` (audit-cited dead re-export that defined no
task; nothing imports it; removes the "zero tasks" placeholder).

### Step 5 — Document the broker convention (`backend/.env.example`)

Committed example (no secrets) documenting `CELERY_BROKER_URL`,
`CELERY_RESULT_BACKEND`, `REDIS_URL`, `CELERY_INTEGRATION` opt-in flag, and the local
values a developer needs. `backend/.env` stays gitignored.

### Step 6 — Unit tests (`backend/apps/core/tests/test_celery.py`)

1. Celery app imports (`config.celery.app` is `cetrak`) and configures from Django
   settings.
2. Broker/result settings are env-driven, credential-free, and set (no `None`).
3. JSON-only serializers + accepted content; `pickle` not accepted.
4. `CELERY_TIMEZONE` equals Django `TIME_ZONE`.
5. Test settings enable eager mode + eager propagation.
6. `config.settings.base` does **not** define `CELERY_TASK_ALWAYS_EAGER`
   (production/development can never accidentally run eager).
7. `core.ping` is registered (autodiscovery) and `.delay(...)` returns the expected
   payload under eager mode (execution path proven).
8. A raising task under eager mode propagates (deterministic failure behavior).

### Step 7 — Opt-in integration test (`backend/apps/core/tests/test_celery_integration.py`)

`pytest.mark.skipif(os.environ.get("CETRAK_CELERY_INTEGRATION") != "1", ...)` — a real
broker/worker round-trip (`ping.apply_async(...).get(timeout=...)`) that only runs when
an operator opts in with the compose `worker` profile up. The default suite never
touches Redis.

### Step 8 — Verification

- Targeted: `py -m pytest apps/core/tests/test_celery.py apps/core/tests/test_celery_integration.py -q`
- Full backend: `py -m pytest apps/ -q` (with `DJANGO_SETTINGS_MODULE=config.settings.test`)
- Migrations: `py manage.py makemigrations --check --dry-run`
- Lint/build: none configured for backend beyond pytest; frontend untouched (no
  frontend files changed → no build required).
- Security review: no secrets, no pickle, no credential-bearing URLs, no eager in prod,
  no new endpoints, no broker/result exposure in compose beyond the existing services.

## Gates

Constitution §VII satisfied (async infrastructure with a real, tested execution path);
§VI, §I–§IV, §V untouched (no auth/accounting/API/tenant change); MVP discipline —
no feature added beyond the infrastructure proof task.

## Constitution Check

Satisfies §VII ("All heavyweight tasks MUST be async (Celery)") by making the async
path deterministic, discoverable, and provably executable. No other principle is
affected or violated.
