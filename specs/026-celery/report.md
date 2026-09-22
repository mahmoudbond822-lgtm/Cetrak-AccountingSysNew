# AUD-026 — Celery Background Task Foundation: Implementation Report

**Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Tasks**: [tasks.md](./tasks.md)

## Current State (before this change)

- Django **6.0.4**; Celery **5.6.3** installed; redis-py **7.4.0** installed.
  `requirements/base.txt` already pinned `celery>=5.3,<6.0` and `redis>=7.0,<8.0` — no
  dependency change was required.
- Celery app: single standard object already present (`config/celery.py` —
  `Celery("cetrak")` + `config_from_object(..., namespace="CELERY")` +
  `autodiscover_tasks()`), exported by `config/__init__.py` as `celery_app`. Left
  **unchanged**; no duplicate app instance was created.
- Config gap: `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` existed **only** in
  `dev.py`; `base.py`/`prod.py`/`test.py` had none → under prod/test
  `app.conf.broker_url` was `None` (verified). Zero tasks existed (audit finding
  AUD-026: "Celery app + worker service exist but zero tasks are defined").
- Redis: already part of the architecture — compose runs `redis:7-alpine` (healthcheck,
  **not** exposed to the host), `dev.py` uses it as the Django cache, and a `worker`
  service (`celery -A config worker -l info`, profile `worker`) with explicit
  `CELERY_*` env already existed. No compose change was needed.
- Task/schedule count before: **0** tasks, no beat, no `.delay`/`apply_async` anywhere.

## Audit Scope

- **Required** (this change): deterministic Celery configuration in `base.py` that
  reaches all environments; env-driven Redis broker/result (existing convention);
  JSON-only serialization/accepted content; UTC/timezone consistency with Django;
  reliable autodiscovery; one infrastructure proof task so §VII has a real execution
  path; test-only eager mode with a prod-guard; documented broker environment
  convention; full regression with zero behavior change.
- **Optional** (deferred, documented): the audit-recommended first *business* async job
  (audit-mail / memo dispatch, AUD-015 adjacency), Celery Beat / scheduling, retries.
- **Out of scope**: Flower/monitoring/K8s/production orchestration, `render.yaml`,
  accounting/auth/API/frontend changes, dependency upgrades, unrelated audit findings,
  Dashboard v2, AI Foundation.

## Implementation

| File | Change |
| --- | --- |
| `backend/config/settings/base.py` | Added the full Celery block: env-driven `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` (local-only defaults, no credentials/host hard-coded), JSON task/result serializers, JSON-only `CELERY_ACCEPT_CONTENT`, `CELERY_TIMEZONE = TIME_ZONE`, `CELERY_ENABLE_UTC = True`, `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True`. Now inherited by dev/local/test/prod. |
| `backend/config/settings/dev.py` | Removed the two now-redundant broker/result override lines (single source of truth in `base.py`). Behavior preserved (compose worker passes explicit env; out-of-compose dev now correctly defaults to `localhost` instead of the unresolvable compose hostname). |
| `backend/config/settings/test.py` | Added `CELERY_TASK_ALWAYS_EAGER = True` and `CELERY_TASK_EAGER_PROPAGATES = True` — deterministic, Redis-free unit tests that surface failures instead of swallowing them. Never imported by prod/dev. |
| `backend/apps/core/tasks.py` | **New**: `core.ping` — idempotent infrastructure proof task (JSON-safe `{task_id, message}` return; no DB, request, session, or credentials; no internal exception swallowing). Autodiscovered from `apps.core`. |
| `backend/apps/accounts/tasks.py` | **Deleted** — audit-cited dead re-export that defined zero tasks; nothing imported it. |
| `backend/.env.example` | **New**: documents `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_URL`, and the `CETRAK_CELERY_INTEGRATION` opt-in flag with local values only. `backend/.env` stays gitignored. |
| `backend/apps/core/tests/test_celery.py` | **New**: 19 unit tests (app import/config, env-driven + credential-free URLs, JSON-only serialization, timezone, broker retry, discovery/registration, eager execution of `core.ping`, eager exception propagation, base-settings eager guard). |
| `backend/apps/core/tests/test_celery_integration.py` | **New**: opt-in real broker/worker round-trip, skipped unless `CETRAK_CELERY_INTEGRATION=1` (default suite never touches Redis). |
| `config/celery.py`, `config/__init__.py`, `docker-compose.yml`, `render.yaml`, `requirements/*` | **Untouched** (worker + redis already present; deployment out of scope). |

- **Task discovery**: `autodiscover_tasks()` at worker startup imports `apps.*.tasks`
  (verified: all discovered modules import cleanly and `core.ping` is registered).
- **Worker**: existing compose `worker` service (`celery -A config worker -l info`,
  profile `worker`) runs unchanged against the now-deterministic settings; broker
  retry-on-startup makes boot ordering safe.

## Task Safety

- **Serialization**: JSON-only task payloads and results; worker accepts only `json`
  content — no pickle execution path from the broker or into the result backend.
- **Retry behavior**: none added — AUD-026 does not require retries and speculative
  `autoretry_for` semantics would invent behavior.
- **Failure behavior**: no `try/except` swallowing in `core.ping`; a raising task is
  recorded as FAILURE in the result backend, and under eager mode propagates to the
  caller (tested).
- **Transaction handling**: no enqueue site exists yet, so no `transaction.on_commit`
  wiring was needed; the rule is documented (any future DB-triggered send must use
  `transaction.on_commit`). No transactional/accounting behavior was modified.
- **Idempotency**: `core.ping` is a pure function of its argument — duplicate
  execution is harmless by construction.

## Environment Variables

- `CELERY_BROKER_URL` (default `redis://localhost:6379/0`) — broker.
- `CELERY_RESULT_BACKEND` (default `redis://localhost:6379/0`) — result backend (Redis
  db 0; the Django cache uses db 1 via existing `REDIS_URL`).
- `CETRAK_CELERY_INTEGRATION=1` — opts into the real-broker integration test.
- Documented in `backend/.env.example`; `backend/.env` (dev values) remains gitignored.

## Tests

- Targeted: `py -m pytest apps/core/tests/test_celery.py apps/core/tests/test_celery_integration.py -q`
  → **19 passed, 1 skipped** (integration, correct default).
- Full backend: `py -m pytest apps/ -q` (settings `config.settings.test`) →
  **455 passed, 2 skipped**, **0 failed** (436 pre-existing + 19 new; skips = 1
  pre-existing + 1 opt-in integration). No auth/accounting/tenant/jwt regressions.
- Migrations: `py manage.py makemigrations --check --dry-run` → **"No changes detected"**.
- Lint/type checks: none configured for the backend beyond pytest; frontend untouched
  (no frontend files changed → no build required).
- Pre-existing failures: **none** (the 2 skips are intentional, not failures).

## Security Review

- Secrets: none committed. `base.py` defaults carry no credentials or production host;
  `backend/.env.example` is local values only; `.env` is gitignored (verified with
  `git check-ignore`).
- Password/token handling: untouched; `core.ping` accepts no credentials, stores no
  tokens, logs nothing.
- Serialization safety: JSON-only task/result serializer and accepted content — pickle
  is rejected outright (asserted by test).
- Broker exposure: compose `redis` service has **no host port mapping** (container-only);
  worker is private to the compose network; no new endpoints/service exposure was added.
- Result backend exposure: results live on Redis db 0, JSON-encoded, subject to Celery's
  default result expiry; no web-accessible result API exists.
- Production eager mode: impossible — `CELERY_TASK_ALWAYS_EAGER` is defined only in
  `test.py` (which prod/dev never import) and a unit test guards `base.py` against it.

## Spec-Kit

- `specs/026-celery/spec.md` — problem, current state, required outcome, architecture,
  configuration requirements, task requirements, failure semantics, transaction safety,
  testing strategy, environment requirements, acceptance criteria, explicit non-goals.
- `specs/026-celery/plan.md` — verified current state + concrete implementation steps.
- `specs/026-celery/tasks.md` — 26 independently verifiable tasks, all checked.
- `specs/026-celery/report.md` — this report.

## Git

- Commit: `fix(infra): harden celery background task infrastructure`
- Files staged: settings (base/dev/test), `apps/core/tasks.py` + celery tests, deleted
  `apps/accounts/tasks.py`, `backend/.env.example`, `specs/026-celery/*`, AGENTS.md.
  Nothing pushed.