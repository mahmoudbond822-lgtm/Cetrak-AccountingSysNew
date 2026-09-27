# Production Readiness Verification — `7d0c5a7`

**Verified commit:** `7d0c5a7` (`feat(core): add an auditable tenant decommission workflow (AUD-012)`)
**Branch:** `014-auto-customer-code`
**Working tree:** clean, no uncommitted changes
**Date of verification:** 2026-09-27
**Containers:** both throwaway verification databases removed; no stray containers

**Verdict: the commit itself is production-ready. The deployment manifest around it is
not.** Nothing found is a regression introduced by `7d0c5a7` or `8181ccd`; the two
blockers below are pre-existing gaps in `render.yaml` that this stream surfaced but did
not introduce. Details and evidence in §3.

---

## 1. What was verified

| # | Check | Method | Result |
| --- | --- | --- | --- |
| 1 | Working tree state | `git status --porcelain` | clean |
| 2 | **Full migration chain from zero on PostgreSQL 15** | fresh container, `manage.py migrate` | **47/47 applied, exit 0** |
| 3 | Schema invariants after that migration | direct `pg_catalog` queries | **9/9 pass** |
| 4 | Full test suite on real PostgreSQL 15 | `pytest apps/ -q` | **603 passed, 5 skipped, 25 subtests** |
| 5 | Full test suite on SQLite (project default) | `pytest apps/ -q` | **601 passed, 6 skipped, 25 subtests** |
| 6 | Model/migration state agreement | `makemigrations --check --dry-run` | No changes detected |
| 7 | Migration idempotency on a **populated** database | `manage.py migrate` | No migrations to apply |
| 8 | Destructive-migration scan | static scan of all 27 migrations | none found |
| 9 | **Django's own production check** | `check --deploy` with `config.settings.prod` | **no issues (0 silenced)** |
| 10 | Production fail-fast guards | booted `prod` with bad config | both refuse correctly |
| 11 | Secret hygiene | pattern scan + `git ls-files` | clean |
| 12 | Deploy manifest vs code env vars | cross-referenced | **2 gaps — see §3** |
| 13 | Frontend build | `npm run build` | clean, 444.15 kB JS / 11.67 kB CSS |
| 14 | Frontend lint | `npm run lint` | 13 problems — unchanged baseline |

### 1.1 The deploy path itself now works

Check 2 is the one that matters most and was impossible before this stream. A fresh
PostgreSQL 15 database, migrated from zero, applies cleanly end to end — including
`accounting/0005_decimal_exact_balance_check`, which failed on every PostgreSQL database
before `8181ccd`. `render.yaml` runs exactly this command
(`python manage.py migrate --noinput`) as part of its `buildCommand`, so the production
deploy path is now confirmed working end to end.

### 1.2 Schema invariants (check 3)

Verified directly against the freshly migrated database, not inferred from the code:

| Invariant | Result |
| --- | --- |
| `check_entry_balanced` is Decimal-exact (no `0.01` tolerance, no `ABS`) | PASS |
| `balanced_entry_check` constraint installed on `accounting_journalentry` | PASS |
| **No tenant FK carries `ON DELETE CASCADE`** | PASS (0 of 22) |
| 22 tenant foreign keys present | PASS |
| `decommissioned_at` / `decommissioned_by` nullable (stamped only on decommission) | PASS |
| `decommission_reason` `NOT NULL` with a `''` default | PASS |
| `decommissioned_by` FK does not cascade | PASS (action `a`) |
| 32 tables created | PASS |

### 1.3 The two guard rails are live, not decorative (check 10)

`prod.py`'s fail-fast paths were exercised by deliberately breaking the configuration:

- insecure `SECRET_KEY` → `ImproperlyConfigured: DJANGO_SECRET_KEY environment variable
  must be set in production.`
- console email backend → `ImproperlyConfigured: EMAIL_BACKEND must be
  'django.core.mail.backends.smtp.EmailBackend' in production; development backends are
  not permitted.`

Production cannot boot with a development secret or a development mail backend.

## 2. Verified clean

- **`prod.py` posture:** `DEBUG=False`; `ALLOWED_HOSTS` from env; `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, one-year HSTS with subdomains and
  preload; `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` for the edge proxy;
  `CORS_ALLOW_ALL_ORIGINS = False`; whitenoise manifest static storage; DB `ssl_require=True`.
- **Secret hygiene:** no live credential patterns (AWS, OpenAI, GitHub, Slack, Google
  private keys) in any tracked config or deploy file. `SECRET_KEY` is env-driven with a
  clearly labelled development fallback that production refuses. `backend/.env` is
  **untracked** and `.gitignore` covers `.env`, `.env.local`, `.env.*.local`.
- **Migration safety:** across all 27 migrations there is no `DeleteModel`,
  `RemoveField`, `RunSQL`, `TRUNCATE`, `DELETE FROM`, `DROP TABLE`, or type-narrowing
  `ALTER COLUMN`. The only 6 `RunPython` operations are 2 constraint-DDL pairs and 4
  tenant backfills that `UPDATE` from the parent row (covered by the existing
  `test_line_tenant_backfill_migration.py` round-trip test).
- **No regression:** 601/603 passing with 29 tests added by this stream, none weakened or
  deleted. The SQLite/PostgreSQL delta of 2 tests is fully explained by
  `test_sales_inventory_api.py:291`, which is vendor-gated and therefore inert on SQLite.
- **Frontend:** build clean; lint at the unchanged 13-problem baseline
  (11× `react-hooks/set-state-in-effect`, 1× `exhaustive-deps`, 1× `no-undef` in
  `vite.config.js`) — all pre-existing, zero new lint debt.

## 3. BLOCKERS — deployment configuration, not this commit

### B1. Production email delivery cannot work, and fails the request

`render.yaml` declares **no Celery broker configuration and no worker service**. Its only
services are `cetrak-api` (web), `cetrak-frontend` (static) and `cetrak-db`. The compose
stack does have a `worker` service, but it is behind `profiles: ["worker"]` and is not the
production deployment.

So in production `CELERY_BROKER_URL` is unset and `base.py:174-175` falls back to
`redis://localhost:6379/0` — a local-only default pointing at the web container itself,
where nothing listens. I reproduced the consequence against a dead broker:

```
enqueue_invitation_email RAISED
  builtins.RuntimeError: Retry limit exceeded while trying to reconnect to
  the Celery result backend. The Celery application must be restarted.
```

This is worse than "email is delayed", because of **where** it is called.
`apps/accounts/views.py:331` wires it through `transaction.on_commit`:

```python
transaction.on_commit(lambda: enqueue_invitation_email(invitation.id))
```

The invitation row is therefore **already committed** when `.delay()` raises. The client
receives a **500**, the invitation persists in the database, and the email is never sent.
A client retry creates a second invitation. The failure mode is silent data-plus-error:
the operator sees a failed request and a tenant admin list that disagrees with it.

The SMTP-failure path *is* handled well (`test_email_task.py:113` covers a failing send
inside the task, which retries). What is untested is a failing **broker publish**, because
`CELERY_TASK_ALWAYS_EAGER = True` in test settings means `.delay()` never touches a broker
in any test. That is the same blind-spot class as the `accounting/0005` defect.

Note that the AUD-015 report (L213) refers to "the worker service (`cetrak-worker`)", which
exists only in the compose stack under a different name. The Render deployment path was
not covered.

### B2. No `REDIS_URL`, so authentication throttling is per-process in production

`render.yaml` does not set `REDIS_URL`. `prod.py` does not silently accept this — it logs:

> `REDIS_URL is not set: authentication throttling state is process-local and every limit
> is effectively multiplied by the number of web workers. Set REDIS_URL to a shared Redis
> instance.`

That warning fires in the manifested deployment, confirmed by running the prod settings.
The web service starts `gunicorn --workers 3`, so every AUD-014 login/refresh limit is
effectively **3× weaker** than designed, and degrades linearly with each additional
instance on scale-out. The AUD-014 report (L327) explicitly recorded that `render.yaml`
was left unchanged and deferred this, so it is a known and documented deferral — but it
means the throttling protection committed in `3cba284` is **not actually active in
production as currently configured**.

Compounding this: the health check cannot detect the condition.
`apps/core/health.py:check_redis()` does `cache.set` / `cache.get`, which **succeed**
against a per-process LocMem cache, so `/api/v1/health/` reports `"cache": "ok"` in a
deployment where the cache is not shared. The endpoint reports `ok` for precisely the
degraded-but-not-down state it exists to detect.

### Fix for both

Both are the same change: provision a Redis instance, set `REDIS_URL`,
`CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`, and add a Render background worker
service running `celery -A config worker -l info`. Additionally, `enqueue_invitation_email`
should catch broker-unavailable errors and log them rather than propagating a 500 after
the commit — an invitation that cannot be emailed should still return 201, because the row
exists and the operator can retry delivery.

## 4. SHOULD-FIX

1. **`migrate` runs in `buildCommand`.** `render.yaml` runs
   `collectstatic && migrate` at build time. Builds can be run speculatively and
   concurrently, and this couples schema mutation to the build step. A release command or
   a `preDeployCommand` is the conventional place for migrations. It works today because
   the chain applies cleanly, but it is fragile as the schema grows.
2. **No `ALLOWED_HOSTS` failure mode is documented.** `ALLOWED_HOSTS` comes from
   `DJANGO_ALLOWED_HOSTS`; if it is ever empty, production fails closed (every request
   rejected) rather than open. Correct behaviour, but the failure mode is a total outage
   with a terse error, and `.onrender.com` will not match a custom domain if one is added.
3. **`SYSTEM_DEFAULT_AI_KEY` is declared in `render.yaml` but read by nothing** in the
   backend. Either dead config or an unimplemented AI feature. Harmless, but it should not
   sit in the manifest implying a capability that does not exist.
4. **The suite has no PostgreSQL by default.** `config/settings/test.py` falls back to
   in-memory SQLite, which disconnects every Postgres-only code path. This is exactly what
   hid the `accounting/0005` deploy blocker through an entire green stream, and it also
   hides the untested broker-publish path in B1. Making PostgreSQL the CI default is the
   single highest-leverage hardening step available.
5. **The test database cannot be dropped at the end of a PostgreSQL run** ("2 other
   sessions using the database"). Harmless in a throwaway container, but something holds a
   connection open past teardown and will eventually make `--reuse-db` behave oddly.

## 5. OBSERVATIONS

- The `AuditLog.tenant` FK is `SET_NULL` at the ORM level and `NO ACTION` in the schema.
  Correct and deliberate: audit rows must outlive what they describe, and a tenant can no
  longer be deleted anyway.
- `decommission_reason` is `NOT NULL DEFAULT ''` in the schema. The service rejects a
  blank reason, so the empty string is only reachable by writing to the model directly.
- The dev database is lightly populated (3 tenants, 3 users, 2 journal entries, 4 lines),
  so the four tenant-backfill migrations have met real rows only at this scale. Their
  logic is covered by a dedicated `TransactionTestCase` that reverts and re-applies them.
- The health check always returns HTTP 200, reporting degradation in the body. Render
  keys off the status code, so a missing database or cache will not trigger a restart
  loop. This is the right choice; only the `cache: ok` false assurance in B2 is a problem.

## 6. Reproducing this verification

```powershell
# fresh PostgreSQL 15 (throwaway)
docker run -d --name cetrak-pg-verify -e POSTGRES_DB=cetrak_verify `
  -e POSTGRES_USER=cetrak_verify -e POSTGRES_PASSWORD=cetrak_verify `
  -p 55433:5432 postgres:15-alpine

cd backend
$env:DJANGO_SETTINGS_MODULE="config.settings.test"
$env:POSTGRES_DB="cetrak_verify"; $env:POSTGRES_USER="cetrak_verify"
$env:POSTGRES_PASSWORD="cetrak_verify"; $env:POSTGRES_HOST="127.0.0.1"; $env:POSTGRES_PORT="55433"

py manage.py migrate                       # full chain from zero
py -m pytest apps/ -q -p no:randomly       # 603 passed, 5 skipped
py manage.py makemigrations --check --dry-run

# Django's production check
$env:DJANGO_SETTINGS_MODULE="config.settings.prod"
py manage.py check --deploy                # no issues

docker rm -f cetrak-pg-verify
```
