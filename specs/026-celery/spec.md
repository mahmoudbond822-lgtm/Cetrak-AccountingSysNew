# Feature Specification: AUD-026 — Celery Background Task Foundation

**Feature**: AUD-026 production-safe Celery background-task infrastructure
**Created**: 2026-09-22
**Status**: Draft

## Problem Statement

The project constitution (§VII) requires that "All heavyweight tasks MUST be async
(Celery)." The repository already carries a **Celery scaffold** — the finding is that
the scaffold is incomplete and unproven, not that Celery is absent:

1. **Broker/result configuration is dev-only.** `CELERY_BROKER_URL` and
   `CELERY_RESULT_BACKEND` are declared **only** in `config/settings/dev.py`.
   `config/settings/base.py` declares no Celery settings at all, so `prod.py` and
   `test.py` (both of which import `base.py`, not `dev.py`) have **no broker or result
   backend**. A worker or task dispatch under production settings would connect to
   nothing (Celery falls back to its own default broker, not the repo's Redis). This is
   non-deterministic configuration.
2. **Zero tasks are defined.** `apps/accounts/tasks.py` re-exports the `celery_app`
   object and defines no task. A repository-wide search for `shared_task`, `@task`,
   `.delay(`, and `apply_async` returns **zero** matches — nothing in the application is
   executed asynchronously, so the async path has never been exercised end-to-end.
3. **No deterministic test-mode contract.** `test.py` does not configure Celery eager
   mode, so unit tests cannot exercise task execution without a live broker, and there is
   no assertion that eager mode is confined to tests.
4. **Serialization/timezone safety is implicit, not asserted.** Nothing declares
   JSON-only serialization, JSON-only accepted content, or a worker timezone aligned
   with Django's `TIME_ZONE`/`USE_TZ`, so behavior depends on Celery library defaults
   rather than on this repository's configuration.
5. **No documented broker convention for a fresh checkout.** `dev.py` and
   `docker-compose` use `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`, but there is no
   committed example file documenting them.

This was recorded as **AUD-026 (P2)** in `docs/audits/production-readiness-audit-001.md`
and re-verified as open in audits 003 and the H2 hardening report.

## Required Outcome

Close AUD-026 with the **smallest production-safe implementation**:

- deterministic Celery configuration that exists in `base.py` and therefore applies to
  dev, local, test, and prod;
- Redis broker/result configuration driven by environment variables (reusing the
  repo's existing convention), with no hard-coded infrastructure or credentials;
- correct Django integration (existing single `config.celery` app object, settings
  namespace, autodiscovery) with no duplicate app instances;
- reliable task discovery from installed Django apps;
- at least one **infrastructure-level** task proving the pipeline executes;
- deterministic, documented test behavior (eager mode in tests only, with an assertion
  that production/development settings do not enable it);
- no regression to synchronous application behavior.

## Current State (verified this session)

- Celery **5.6.3** installed (`requirements/base.txt`: `celery>=5.3,<6.0`).
- Redis client **7.4.0** installed (`requirements/base.txt`: `redis>=7.0,<8.0`).
- `config/celery.py` already defines the single standard app:
  `Celery("cetrak")` + `config_from_object("django.conf:settings", namespace="CELERY")`
  + `autodiscover_tasks()`; `config/__init__.py` exports it as `celery_app`.
- Redis is already part of the architecture: `infra/docker-compose.yml` runs a
  `redis:7-alpine` service with a healthcheck, and `dev.py` uses Redis as the Django
  cache (`REDIS_URL`, db 1).
- `docker-compose.yml` already defines a `worker` service (`celery -A config worker -l
  info`, profile `worker`) with explicit `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`
  env (`redis://redis:6379/0`) and correct `depends_on` ordering.
- `requirements/base.txt` already declares celery + redis — **no dependency change
  required**.
- Broker/result URLs exist only in `dev.py`; `base.py`, `prod.py`, `test.py` have none.
  Verified: under `config.settings.test`, `app.conf.broker_url` is `None`.
- Task count: **0**. No scheduling (`beat`, `PeriodicTask`) exists anywhere.
- Existing background jobs: none (audit mail / memo dispatch are explicitly **deferred**,
  per audits 003/H2).
- Tests: `pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings.test`; test
  settings use SQLite in-memory when Postgres env is absent.

## Architecture

```
config/
    celery.py          # single Celery app (existing, unchanged)
    __init__.py        # exports celery_app (existing, unchanged)
    settings/
        base.py        # + ALL Celery config (env-driven broker/result, JSON, UTC)
        dev.py         # + broker/result overrides removed (now inherited from base)
        test.py        # + eager mode ON (test-only) with exception propagation
        prod.py        # unchanged (inherits deterministic config from base.py)
apps/
    core/
        tasks.py       # apps.core.tasks.ping — infrastructure proof task
```

- One Celery application object, settings-namespaced under `CELERY_*`.
- `autodiscover_tasks()` imports `tasks.py` from every installed app
  (`apps.core`, `apps.accounts`, `apps.accounting`, `apps.sales`, `apps.purchases`,
  `apps.inventory`) at worker startup.
- Worker lifecycle stays in Docker Compose (`worker` profile) — no new orchestration.

## Configuration Requirements

All in `base.py` (single source of truth), every non-default setting justified:

| Setting | Value | Concrete reason |
| --- | --- | --- |
| `CELERY_BROKER_URL` | `os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")` | Env-driven; default is local-only, no production host/credential hard-coded; fixes prod/test having no broker at all. |
| `CELERY_RESULT_BACKEND` | same pattern, same default | Results stored on Redis db 0 (matches existing repo convention). |
| `CELERY_TASK_SERIALIZER` | `"json"` | Safe serialization; pickle-based task serialization is forbidden. |
| `CELERY_RESULT_SERIALIZER` | `"json"` | Results persisted to Redis must not be pickle/code-execution payloads. |
| `CELERY_ACCEPT_CONTENT` | `["json"]` | Worker rejects any non-JSON message body — hard guarantee against pickle acceptance from the broker. |
| `CELERY_TIMEZONE` | `TIME_ZONE` (`"UTC"`) | Worker timezone matches Django `USE_TZ`/`TIME_ZONE` so any future date logic agrees. |
| `CELERY_ENABLE_UTC` | `True` | Explicit UTC normalization alongside `CELERY_TIMEZONE`; removes reliance on library default. |
| `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP` | `True` | Deterministic worker startup (broker may come up a beat later) and removes the Celery 5.3+ deprecation warning. |

Not set (deliberately, with reasons): no `task_always_eager` outside `test.py`; no
retry policy (spec §Failure Semantics); no beat/periodic scheduling; no custom worker
infrastructure, queues, or concurrency settings; no `result_expires`/time-limit values
invented from online examples.

## Task Requirements

Exactly one task is introduced — an **infrastructure proof task**, not business logic:

- `apps.core.tasks.ping` (registered name `core.ping`).
- Pure function of its argument: no database access, no request/session object, no
  credentials in arguments or logs, JSON-only payload, idempotent by construction
  (same input → same output, no side effects).
- Returns a small JSON-safe dict (`task_id`, `message`) so a round-trip through
  broker → worker → result backend can be asserted.
- Explicit failure behavior: no internal `try/except` swallowing; an exception inside
  a task propagates as a task failure (and to the caller under eager mode).

Existing public behavior of every other task-like code path is untouched because none
exists today.

## Failure Semantics

- **No speculative retry configuration.** AUD-026 does not require retries; adding
  `autoretry_for`/`max_retries` to the proof task would invent semantics. Documented as
  out of scope.
- Task failures are visible, never swallowed: eager mode in tests propagates
  (`CELERY_TASK_EAGER_PROPAGATES = True`); in workers a raised exception marks the task
  `FAILURE` and is recorded in the Redis result backend.
- Duplicate execution: harmless for `ping` (idempotent); any future business task must
  declare its own idempotency contract before adoption.

## Transaction Safety

No code path currently enqueues a task from within a database transaction (there were
zero enqueue sites before this change, and this change adds none). The infrastructure
requires no `transaction.on_commit(...)` wiring today. The rule is documented for the
future: **any task triggered by a DB mutation must be enqueued inside
`transaction.on_commit(...)`** so workers never read uncommitted rows. No accounting or
transactional behavior is modified.

## Testing Strategy

- **Unit tests (default suite, no Redis required):**
  - app imports and is configured from Django settings;
  - settings assertions: broker/result env-driven and credential-free, JSON-only
    serialization/accept content, timezone matches Django, eager mode ON in tests;
  - `core.ping` is registered by autodiscovery and executes correctly under eager mode;
  - eager mode propagates task exceptions (deterministic failure behavior);
  - `config/settings/base.py` does **not** enable eager mode (guard against eager
    leaking into production/dev).
- **Integration test (opt-in only):** a real broker/worker round-trip test that runs
  **only** when `CETRAK_CELERY_INTEGRATION=1` is set (documented, requires the compose
  `worker` profile). Default suite skips it — tests never depend on a developer
  manually starting Redis.
- Full existing backend suite must keep passing; migrations unchanged.

## Environment Requirements

Existing convention retained: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (plus the
pre-existing `REDIS_URL` for the cache). Documented in a committed
`backend/.env.example` with local/dev values only. `backend/.env` stays gitignored;
no credentials are committed. `docker-compose.yml` continues to supply its own explicit
values for the `worker` service.

## Acceptance Criteria

- [ ] `base.py` defines the full Celery configuration; `dev.py` broker overrides removed.
- [ ] Broker/result backend are environment-driven with local defaults only.
- [ ] Single existing `config.celery` app; no duplicate instances; autodiscovery works.
- [ ] At least one registered, tested, idempotent infrastructure task exists.
- [ ] JSON-only serialization and accepted content (no pickle path).
- [ ] Worker timezone matches Django timezone.
- [ ] Test settings enable eager mode; a test proves base (prod/dev) settings do not.
- [ ] Unit tests require no Redis; integration test is opt-in only.
- [ ] No secrets committed; broker/result URLs contain no credentials.
- [ ] Full backend regression passes; migrations check clean.
- [ ] Spec-Kit artifacts (`spec.md`, `plan.md`, `tasks.md`, `report.md`) complete.
- [ ] No accounting, auth, frontend, API-contract, or deployment changes.

## Explicit Non-Goals

- **Not** implementing audit mail, invitation email delivery, report/export async jobs,
  memo dispatch, reconciliation, or any business-logic task (that is AUD-015/AUD-026
  "first async feature" follow-up work — deferred, per audits 003/H2).
- **Not** Celery Beat / `django-celery-beat` / `PeriodicTask` / any scheduling.
- **Not** Flower, monitoring, metrics, autoscaling, Kubernetes, or production orchestration
  changes (deployment is out of scope; `render.yaml` untouched).
- **Not** a redesign of the async architecture (existing `config/celery.py` stays).
- **Not** adding `task_acks_late`, custom queues, routing, or worker concurrency tuning
  absent a concrete need.
- **Not** Redis dependency/version upgrades; `requirements/*.txt` untouched.
- **Not** Dashboard v2, AI Foundation, unrelated audit findings, or any frontend change.
