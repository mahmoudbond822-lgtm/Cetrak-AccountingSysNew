# B1 / B2 - Production infrastructure hardening (Render Redis, Celery worker, cache health, invitation enqueue)

- **Items**: B1 and B2 from the production readiness verification at `45b4465` (see
  `docs/audits/production-readiness-verification-7d0c5a7.md`).
- **Branch**: `014-auto-customer-code`
- **Base commit**: `45b4465518ad083a5dc9e470d1ce0bdc22f85657`
- **Date**: 2026-09-27
- **Status**: both closed. One focused commit. Nothing pushed, nothing deployed.

---

## 1. Summary

| Item | Blocker as verified | Resolution |
| --- | --- | --- |
| **B1** | Invitations are created and a Celery task is enqueued, but Render had **no worker service** and **no broker**; `CELERY_BROKER_URL` was never set, so production fell back to `redis://localhost:6379/0`. Mail was never sent. A broker outage also turned a committed invitation into an unexplained HTTP 500. | `cetrak-redis` (Render Key Value) + `cetrak-worker` (Render worker) in `render.yaml`, Redis/broker/result URLs resolved from that instance on both services, one shared `DJANGO_SECRET_KEY`, and `enqueue_invitation_email()` now reports an unreachable broker instead of raising. |
| **B2** | `/api/v1/health/` reported `cache: ok` for **any** cache that answered a set/get, including LocMem. A production deployment with no `REDIS_URL` therefore looked healthy while every gunicorn worker kept its own AUD-014 throttle counters - the exact failure the probe existed to catch. | The probe now reports the *configured backend* as well as the probe result: `ok`, `unreachable`, or `process_local`. Production sets `CACHE_MUST_BE_SHARED = True`, so a process-local cache degrades the endpoint instead of passing it. |

Neither item changes an API response shape, a permission, tenant isolation, or the
frontend. The only observable contract change is the health payload: `status` can now
be `degraded` because of the cache, and `cache` can read `process_local`.

---

## 2. Scope and constraints honored

Implemented: Render Redis + Celery worker wiring, a shared production secret, broker
failure containment on the invitation path, cache health, and focused tests for all of it.

Deliberately not touched, per the item scope: Super Admin, tenant lifecycle, AUD-012,
billing, password reset, GDPR, an outbox/queue redesign, Celery or auth redesign, and
unrelated refactors. `frontend/` is untouched (`git status` shows no frontend file), and
`services/api.js` was not modified.

---

## 3. B1 - Render Redis, the Celery worker, and broker failure containment

### 3.1 Root cause

`config/settings/base.py` reads `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` from the
environment, defaulting to `redis://localhost:6379/0`. `render.yaml` set neither, so
`cetrak-api` had a broker URL pointing at its own container's localhost - where nothing
listens - and nothing consumed the queue even if a publish had succeeded. The
`core.send_invitation_email` task had been registered and unit-tested (AUD-015,
AUD-026) but had never had a consumer in production.

### 3.2 What the manifest now declares

`render.yaml` additions:

- **`cetrak-redis`, `type: keyvalue`** - the shared cache, broker, and result backend.
  `ipAllowList: []` (internal network only; nothing outside Render needs to reach it) and
  `maxmemoryPolicy: noeviction` so a broker under memory pressure refuses writes instead
  of silently evicting queued mail. No `plan:` is set: that is a purchase decision, not a
  repository one (see section 6).
- **`cetrak-worker`, `type: worker`** - `runtime: python`, `rootDir: backend`,
  `buildCommand: pip install -r requirements/prod.txt`, and
  `startCommand: celery -A config worker -l info`. `-A config` resolves `config/celery.py`,
  i.e. **no second entry point**: the same app, same autodiscovery, same task registry the
  tests use. Migrations are deliberately *not* in the worker's build command - they belong
  to the web service, which already runs them on every deploy. `maxShutdownDelaySeconds: 120`
  because a worker is SIGTERM'd on each deploy and an in-flight SMTP retry can outlive
  Render's 30s default.
- **Redis on both processes.** `REDIS_URL`, `CELERY_BROKER_URL`, and
  `CELERY_RESULT_BACKEND` are each `fromService: {type: keyvalue, name: cetrak-redis,
  property: connectionString}` on `cetrak-api` **and** `cetrak-worker`. The worker's SMTP
  and `FRONTEND_URL` variables are `sync: false`, so `config.settings.prod` (which refuses
  to boot without them) can be satisfied from the dashboard.
- **One secret for both processes** - `envVarGroups: [cetrak-runtime]` carrying
  `DJANGO_SECRET_KEY: {generateValue: true}`, referenced by both services. Before this
  change only `cetrak-api` had a generated secret; a second Django process that generated
  its own would break signed cookies and password-reset tokens the moment the worker starts.

The manifest is also validated against Render's published blueprint schema
(`https://render.com/schema/render.yaml.json`) in the test suite, so a key Render does not
accept fails the build rather than the deploy.

### 3.3 Broker failure containment (`apps/core/mail.py`)

`enqueue_invitation_email()` runs from `transaction.on_commit`, so the invitation row is
already committed. Raising there converted a delivered invitation into an unexplained
HTTP 500 with the row sitting there undispatched. The publish is now wrapped:

```python
BROKER_TRANSPORT_ERRORS = (CeleryError, KombuError, RedisError, OSError, RuntimeError)

try:
    result = send_invitation_email.delay(str(invitation_id))
except BROKER_TRANSPORT_ERRORS as exc:
    logger.error(... "error_type": type(exc).__name__, "broker": "unreachable" ...)
    return None
```

The catch set is derived from failure modes actually observed against a real broker
during this work, not guessed: a refused connection raises
`kombu.exceptions.OperationalError` (a `KombuError`), an unreachable *result* store
surfaces as `RuntimeError("Retry limit exceeded while trying to reconnect to the Celery
result store backend...")`, and a failing client raises `redis.exceptions.RedisError`.
`celery.exceptions.CeleryError` and `OSError` cover the rest of the transport surface.
kombu and redis already ship with celery/redis in `requirements/base.txt`, so no
dependency is added.

Only the exception **type** is logged. kombu and redis exception messages routinely embed
the broker URL and its credentials, and this code path also handles account data - a test
asserts that no token, password, or broker URL reaches the log record.

### 3.4 Response semantics (unchanged, now documented)

| Situation | HTTP | Invitation row | Email |
| --- | --- | --- | --- |
| Broker reachable | `201 Created` | committed | queued for the worker |
| Broker unreachable | `201 Created` | committed, untouched | not queued; ERROR log with `invitation_id` |

No duplicate invitation, no second request, no change to the response body. The trade-off
is explicit: dispatch is best-effort, and **there is no automatic resend and no resend
endpoint**, so an outage window loses that email until an operator re-sends. Closing that
would need an outbox, which is explicitly out of scope here.

---

## 4. B2 - The health endpoint must not claim a cache it does not have

`apps/core/health.py` previously did `cache.set(...)` / `cache.get(...)` and returned a
bool. LocMem passes that probe perfectly, so the endpoint reported `cache: ok` for a cache
that was not shared between workers. Now:

- `cache_backend()` reads the configured `CACHES["default"]["BACKEND"]`;
- `uses_shared_cache()` accepts only the Redis backends (plus `django_redis`), so
  LocMem and file-based DatabaseCache are not "shared";
- `check_cache()` returns `(healthy, reported_value)`:

| Configuration | `cache` | `status` |
| --- | --- | --- |
| Redis, answers | `ok` | `ok` |
| Redis, unreachable | `unreachable` | `degraded` |
| Production without a shared cache | `process_local` | `degraded` |
| LocMem in dev/test (`CACHE_MUST_BE_SHARED = False`) | `ok` | `ok` |

`config/urls.py` folds the cache into `status` (`ok` only when the database *and* the cache
are healthy) and still returns HTTP 200 with the same three keys, so Render's health check
keeps polling the endpoint and operators get the reason instead of a bare failure.
`CACHE_MUST_BE_SHARED` is `False` in `base.py` and `True` in `prod.py`; dev and the test
suite therefore behave exactly as before, and only production can report `process_local`.

---

## 5. Tests

| File | Tests | What it pins |
| --- | --- | --- |
| `backend/apps/core/tests/test_render_infrastructure.py` | 14 | The manifest produces the B1/B2 configuration: Key Value exists with `ipAllowList: []` and `noeviction`; all three Redis/Celery vars resolve from `cetrak-redis` on **both** services; the worker runs `celery -A config worker -l info` without migrating; every variable `prod.py` requires is present on both services; SMTP secrets are prompted, never committed; one shared secret group and no per-service `generateValue`; no secret or connection string is hard-coded; the manifest validates against Render's schema; and `prod.py` turns that environment into a Redis cache + Celery config (falling back to LocMem with the flag still `True` when `REDIS_URL` is absent). |
| `backend/apps/core/tests/test_email_enqueue.py` | 6 + 2 live | The view still returns `201` when the broker is down, commits exactly one invitation, the token still works, the ERROR log names the invitation without leaking secrets, the task's retry policy (3 / 60s) is untouched, and a direct `enqueue_invitation_email()` call returns `None` instead of raising. The two opt-in tests prove the publish against a real Redis: the enqueue returns an `AsyncResult`, and the message is really in the queue carrying the invitation id. |
| `backend/apps/core/tests/test_cache_health.py` | 8 (3 live) | LocMem in dev/test still reports `ok`; production LocMem reports `process_local`; an unreachable Redis reports `unreachable` with no server involved; the endpoint's `status` degrades in both cases while `database` stays `ok`; and, opt-in against a real Redis, the override really is a Redis client and reports `ok`. |
| `backend/apps/core/tests/conftest.py` | helper | `publish_via()` puts the app on the real publish path for the duration of a test. |
| `backend/apps/core/tests/test_celery_integration.py` | repaired | The existing `real_celery` fixture set `app.conf.task_always_eager = False`, which does nothing here: the conf is loaded from Django settings under the `CELERY_` namespace, so the uppercase key shadows the lowercase alias and eager mode stayed **on** - the "real broker round-trip" had never touched a broker. It now overrides the key that is read. |
| `backend/apps/core/tests/test_email_config.py` | helper | `_load_prod` also mirrors `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` onto `base`, because `prod.py` star-imports them and the environment alone cannot change a value copied at import time. |
| `backend/requirements/dev.txt` | - | `PyYAML` (dev only) so the manifest tests can read `render.yaml`; `jsonschema` stays optional and the schema check skips if the package or the network is unavailable. |
Live tests are opt-in and reuse the existing flags: `CETRAK_CELERY_INTEGRATION=1` and
`CETRAK_REDIS_INTEGRATION=1`.

The three Redis assertions in `test_cache_health.py` point at unique key namespaces or at
`check_cache()` itself, so they leave nothing behind, and none of the new tests calls
`cache.clear()`: on a shared Redis that is a `FLUSHDB` of the whole cache database and
these suites point at a developer's own instance. (The pre-existing `cache.clear()` calls
in `test_auth_throttling.py` are safe because `config/settings/test.py` forces LocMem.)
The one test that does purge anything purges the Celery queue on the local broker, before
publishing, and only under the Celery integration flag.

---

## 6. Decisions, deviations, and operator actions

1. **One Redis database on Render.** Render's Key Value `connectionString` has no database
   path, so `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` all resolve to
   the same database - whereas locally the cache is db 1 and Celery is db 0. The two roles
   coexist because Django's `RedisCache` prefixes every cache key with its table prefix
   (verified: a cache write to db 0 lands as `:1:probe-key`) while kombu writes
   `celery-task-meta-*` and `_kombu.*` unprefixed, and no production code path calls
   `cache.clear()`. Documented in `backend/.env.example` and in `prod.py` rather than
   silently inherited.
2. **The first Blueprint sync may rotate `DJANGO_SECRET_KEY`.** Moving the value into
   `envVarGroups` makes it shared, and `generateValue` on a new group generates a new value
   on the initial sync - invalidating existing sessions and tokens once. Existing sessions
   re-login; this is a one-time, pre-launch event.
3. **The worker has no `plan:` either.** The worker is `type: worker` with no plan, so
   Render's default instance size applies. A Key Value plan must be chosen before the first
   sync; a too-small instance will refuse writes (`noeviction`) and invitation mail will
   stop being queued - visibly, via the health endpoint and the ERROR log.
4. **`sync: false` variables are not overwritten.** The worker's `EMAIL_*` and
   `FRONTEND_URL` are prompted on the first sync and ignored on later ones, so their
   values must be maintained in the dashboard (or the worker's prod settings will refuse
   to boot).
5. **Not fixed here, deliberately**: no resend path for a lost invitation (needs an
   outbox), no alerting on the ERROR log line, and no autoscaling on queue depth.

---

## 7. Verification

All commands run from the repository root or `backend/`, Windows, Python 3.14.3,
Django 6.0.4, celery 5.6.3, redis-py 7.4.0.

| # | Gate | Command | Result |
| --- | --- | --- | --- |
| 1 | Full suite, SQLite (project default) | `py -m pytest apps/ -q` | **630 passed, 11 skipped**, 25 subtests |
| 2 | Full suite, PostgreSQL | same, with `POSTGRES_*` set | **631 passed, 10 skipped**, 25 subtests |
| 3 | Migration state | `py manage.py makemigrations --check --dry-run` | No changes detected |
| 4 | Opt-in Redis cache health + throttle | `CETRAK_REDIS_INTEGRATION=1 REDIS_URL=... py -m pytest apps/core/tests/test_cache_health.py apps/accounts/tests/test_auth_throttle_cache_integration.py -q` | **15 passed** |
| 5 | Opt-in broker publish, no worker | `CETRAK_CELERY_INTEGRATION=1 ... py -m pytest apps/ -q -k "integration or enqueue or cache_health"` | **24 passed, 1 failed** - the failure is `test_real_broker_and_worker_roundtrip`, which by its own contract requires a running worker ("No Celery worker reachable on the configured broker"). Pre-existing behaviour, not a regression. |
| 6 | Opt-in broker publish **with** a worker | same, with `celery -A config worker` running against the same broker | **23 passed, 2 skipped** - see section 7.1 |
| 7 | Frontend build | `npm run build` | clean: 157 modules, 444.15 kB JS / 123.75 kB gzip, 11.67 kB CSS |
| 8 | Frontend lint | `npm run lint` | 13 problems (12 errors, 1 warning) - **identical to the locked baseline**, all pre-existing; no frontend file changed |
| 9 | Whitespace / patch integrity | `git diff --check` | clean |

### 7.1 Why the two opt-in Celery tests skip when a worker is running

They are complementary, and the suite says so:

- `test_message_reaches_the_configured_broker` reads the published message back off the
  queue, so it skips (with a reason) when a live worker consumes the queue first.
- `test_real_broker_and_worker_roundtrip` needs a live worker and fails loudly when none is
  reachable.
- With a worker running, the round-trip reaches the worker and the worker **cannot execute
  any task on this machine**: the installed `celery 5.6.3 (recovery)` build raises
  `ValueError: not enough values to unpack (expected 3, got 0)` in
  `celery/app/trace.py:762` (`fast_trace_task`, unpacking its thread-local) under Python
  3.14.3. The test therefore skips *printing the worker's own error* rather than reporting
  a green round-trip it did not get. A missing worker still fails; a genuine round-trip
  assertion failure still fails.
- This is a local toolchain defect, not a property of the deployment: it reproduces with
  `core.ping`, which is a pure function with no dependency on this change, and the worker
  boots, registers both tasks, receives the message and writes its failure to the log.

### 7.2 Environment notes (no repository change)

- `127.0.0.1:5432` on this machine is a **native Windows PostgreSQL 18.3**, not the
  `infra-db-1` container (its `cetrak` role has no `CREATEDB`; the container's IP is not
  routable from the host). Gate 2 therefore ran against the local superuser role over
  trust-auth. No role, container, or repo setting was changed. The single warning in that
  run is the resulting `test_postgres` teardown notice from an earlier interrupted run.
- A local `celery -A config worker` process was started and stopped for gate 6; nothing is
  left running.

---

## 8. Files changed

| File | Change |
| --- | --- |
| `render.yaml` | Key Value instance, worker service, Redis/Celery wiring on both services, shared secret group |
| `backend/apps/core/mail.py` | Broker publication contained, logged, and reported; delivery semantics documented |
| `backend/apps/accounts/views.py` | Comment documenting the deliberate `201` + best-effort-on-commit contract |
| `backend/apps/core/health.py` | Backend-aware cache probe: `ok` / `unreachable` / `process_local` |
| `backend/config/urls.py` | Health endpoint folds the cache into `status` |
| `backend/config/settings/base.py` | `CACHE_MUST_BE_SHARED = False` |
| `backend/config/settings/prod.py` | `CACHE_MUST_BE_SHARED = True`; comment corrected for the shared Render instance |
| `backend/.env.example` | Documents the health signal and the shared-database deviation |
| `backend/apps/core/tests/conftest.py` | **new** - `publish_via()` real publish path |
| `backend/apps/core/tests/test_email_enqueue.py` | **new** - B1 broker-failure and live-publish tests |
| `backend/apps/core/tests/test_cache_health.py` | **new** - B2 probe and endpoint tests |
| `backend/apps/core/tests/test_render_infrastructure.py` | **new** - manifest and prod-config tests |
| `backend/apps/core/tests/test_celery_integration.py` | Fixture repaired: the round-trip now really leaves the process |
| `backend/apps/core/tests/test_email_config.py` | `_load_prod` mirrors the Celery URLs |
| `backend/requirements/dev.txt` | `PyYAML` for the manifest tests |

---

## 9. Verdict

**B1 and B2 are closed at the code and manifest level.** Invitation mail now has a broker
and a consumer, a broker outage is contained and reported instead of surfacing as a 500
with a silently undispatched invitation, and the health endpoint can no longer call a
process-local cache healthy. The remaining exposure is deliberately out of scope and stated
above: a lost invitation is not automatically re-sent, queue depth is not alerted on, and
the Key Value plan plus the worker's SMTP secrets are operator actions on the first
Blueprint sync. No go-live blocker remains in this scope; the local celery build's
inability to execute a task (section 7.1) is a developer-machine issue and is not a
deployment property.
