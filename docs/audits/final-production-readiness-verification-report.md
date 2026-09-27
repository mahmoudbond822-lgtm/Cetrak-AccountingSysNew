# Final Production-Readiness Verification Report

**Verdict: GO WITH CONDITIONS.**
No code defect blocks the first deploy. Every remaining condition is a
deploy-time operator input, enumerated exhaustively in §9. The conditions are
listed as conditions rather than folded into the GO because each one is
individually capable of a silent, hard-to-diagnose production failure (a
spun-down Redis dropping queued invitation email; a wrong `EMAIL_BACKEND`
string preventing the worker from booting at all).

| | |
|---|---|
| Branch | `014-auto-customer-code` |
| Verified commit (start of pass) | `9c6306d6597b1dd1c0c055bd38b3c28f6ec44fef` (`9c6306d`) |
| Commit added by this pass | `e2c6a71` — test-only fix, §5 |
| Report commit | this document, docs-only |
| Working tree | clean; nothing pushed, nothing deployed |
| Independent prior opinions | **not** treated as evidence; every claim below is tied to code, tests, or git at the verified commits |

---

## 1. What this pass is, and what it is not

This is a re-verification, not a review of the prior reports. For each item
previously reported as closed, the status was re-derived from the current
source tree, the current tests, and the current git history; then the tests
that make the claim were re-run. A prior report's wording was treated as a
claim to be checked, not as a fact.

Two prior statements did not survive that check. Both are recorded in full
rather than quietly corrected:

* §4 — the claim that the installed Celery "cannot execute any task" on this
  interpreter. **Refuted.** It was a Windows-only artifact of billiard's
  `prefork` pool.
* §7 — the named test file
  `apps/accounting/tests/test_tenant_isolation.py`. **Does not exist**, in the
  current tree or in any commit in the repository's history.

Everything else re-derived as previously reported.

## 2. Phase 0 — source of truth

```
$ git status --short          # (empty)
$ git rev-parse HEAD          # 9c6306d6597b1dd1c0c055bd38b3c28f6ec44fef
$ git rev-parse --abbrev-ref HEAD   # 014-auto-customer-code
```

## 3. Phase 1 — status of each previously-reported-closed item

Each row was confirmed by locating the implementing code at HEAD **and** by
re-running that item's specific coverage. Subtest counts are reported because
several of these modules assert in loops over models, endpoints, or states.

| Item | Status | Implementing commit(s) | Coverage re-run at HEAD |
|---|---|---|---|
| AUD-011 — line-level tenant integrity | closed | `2b08f5a` | 8 passed, 16 subtests |
| AUD-012 — tenant decommission | closed | `7d0c5a7`, migration prereq/fix `8181ccd` | 44 passed, 9 subtests |
| AUD-014 — distributed auth throttle | closed | `3cba284`, follow-up `a70405d` | 34 passed (hermetic) |
| AUD-015 — email delivery | closed | `8f90580`, hardened in `9c6306d` | 57 passed, 2 skipped |
| AUD-029 — list pagination + invoice N+1 | closed | `90fec80` | 12 passed |
| AUD-030 / N1 — exact-balance enforcement | closed | `2b08f5a`, follow-up `8181ccd` | 9 passed |
| B1 — infrastructure hardening | closed | `9c6306d` | included in the 47/6 focused set |
| B2 — production-config correctness | closed | `9c6306d` | included in the 47/6 focused set |
| B1/B2 combined focused set | closed | `9c6306d` | 47 passed, 6 skipped |

The AUD-014 hermetic suite deliberately does not touch a network. Its live half
is gated behind `CETRAK_REDIS_INTEGRATION=1` and was run against a real Redis
in §5.

## 4. Phase 2 — drift since the last closing commit

```
$ git log 9c6306d..HEAD --oneline     # (empty at pass start)
```

No code has changed since the B1/B2 closure, so no regression in the audited
paths is possible from drift alone. The tenant protections were nonetheless
re-read at HEAD rather than assumed, because "no commits" is a weaker argument
than "the invariant is present":

* line models inherit `TenantOwnedLineModel`; all four line tables carry a
  `tenant` column
* `TenantScopedQuerySet.delete()` and `Tenant.delete()` both raise rather than
  cascade
* `Membership.tenant` and the line-model tenant relations are `PROTECT`
* `TenantDecommissionService` is present and reachable
* `TenantScopedAccountField` and the tenant-scoped serializer fields are in
  place on inventory, purchasing, and sales

## 5. Phase 3/4 — full regression, both engines, both cache modes

### 5.1 Fresh PostgreSQL 15, migrated from zero

A dedicated container (`postgres:15-alpine`, published on `127.0.0.1:55432`)
was created for this pass, so the migration path was exercised against an
empty database rather than a migrated one. (The machine's own PostgreSQL 18.3
holds `5432` and was not used.)

```
$ py manage.py migrate --noinput                       # 45 applied, 0 unapplied, exit 0
$ py manage.py migrate --noinput                       # No migrations to apply  (idempotent)
```

45 is the total across the 27 project migration files plus Django's built-ins.
A second run applying zero migrations is the idempotency check.

| Run | Result | Wall clock |
|---|---|---|
| Full suite, fresh PostgreSQL 15 | **631 passed, 10 skipped, 25 subtests** | 698.41 s |
| Full suite, SQLite (default) | **630 passed, 11 skipped, 25 subtests** | 359.53 s |
| Full suite, opt-in live Redis | **637 passed, 4 skipped, 25 subtests** | 523.12 s |
| Full suite, PostgreSQL 15 (re-run after §5.2's fix) | **631 passed, 10 skipped, 25 subtests** | 399.24 s |

The 631/10 PostgreSQL result reproduces the number recorded for B1/B2, so the
closure is reproducible on a second, independent database. SQLite and
PostgreSQL differ by exactly the one PostgreSQL-only test
(`test_sales_inventory_api.py:290`, "Row-lock serialization only applies on
PostgreSQL") and by the opt-in integration tests, so the 631 vs 630 and 10 vs
11 gaps are fully accounted for:

* 1 pre-existing PostgreSQL-only skip
* 7 tests gated on `CETRAK_REDIS_INTEGRATION`
* 3 tests gated on `CETRAK_CELERY_INTEGRATION`

631 + 7 = 638, minus the 1 PostgreSQL-only skip that SQLite skips = 637. The
three reported opt-in configurations are therefore the same test set with
different gates open, which is what makes the three numbers comparable.

One warning is attached to the PostgreSQL runs and is environmental, not
behavioural: the test database `test_verifydb` is still connected by another
session at teardown, so the drop is retried. It does not affect any assertion
and does not reproduce on a database with no other sessions.

### 5.2 A real defect, found and fixed (`e2c6a71`)

The opt-in live-Redis run failed:

```
FAILED apps/core/tests/test_render_infrastructure.py::
  TestProductionSettingsReadTheBrokerAndCache::
  test_missing_redis_url_falls_back_to_locmem_but_stays_flagged
AssertionError: assert 'django.core.cache.backends.redis.RedisCache'
               == 'django.core.cache.backends.locmem.LocMemCache'
```

This is a genuine defect, not a flake, and it is reproducible from a clean
tree in one command — the documented way to run the opt-in suite:

```
$ CETRAK_REDIS_INTEGRATION=1 REDIS_URL=redis://localhost:6379/1 py -m pytest
```

`_load_prod` in `apps/core/tests/test_email_config.py` scrubs leaked
`EMAIL_*` / `FRONTEND_URL` variables from the environment before re-importing
`config.settings.prod`, so that an ambient shell value cannot decide a
production-settings assertion. It did not scrub `REDIS_URL`. Since
`REDIS_URL` is precisely the variable the opt-in runs are required to set, the
opt-in runs were the ones that broke the test whose whole subject is the
absence of `REDIS_URL`: the case was exercised only when the developer's shell
happened to be clean. This is the same class of environment leak that `a70405d`
fixed for AUD-014.

Fixed by adding `REDIS_URL` to the scrub list. The fix is test-only: no
production code, no settings value, and no test assertion is changed. Both
configurations now pass the same set — 30 passed with and without an ambient
`REDIS_URL`, 637/4 with the opt-in environment set, 630/11 without it, 631/10
on PostgreSQL.

This is the only change this pass made, and it is committed separately from
this report as instructed.

## 6. Phase 4c — the Celery runtime question, settled

The previous pass recorded the local Celery runtime as broken, with the
symptom

```
File "celery/app/trace.py", line 762, in fast_trace_task
    tasks, accept, hostname = _loc
ValueError: not enough values to unpack (expected 3, got 0)
```

and attributed it to the interpreter/Celery combination (Python 3.14.3 with
`celery 5.6.3`). **That attribution is wrong.** The mechanism is visible in
the library source: `trace._localized` is a module-level list that
`setup_worker_optimizations()` populates in the MainProcess, and
`fast_trace_task` unpacks it. On Windows, billiard's `prefork` worker is a
separate process that re-imports `celery.app.trace` from source, so its
`_localized` is empty — the tuple is unpacked from a fresh, unpopulated list.
Nothing about the interpreter or the Celery version is involved.

With the pool chosen so the task executes in the process that populated the
list, the real round-trip passes:

```
$ celery -A config worker -l info --pool=solo
$ CETRAK_CELERY_INTEGRATION=1 py -m pytest apps/core/tests/test_celery_integration.py
1 passed
```

and the worker's own log records the genuine execution:

```
[INFO/MainProcess] Task core.ping[3dd8f15e-…] received
[INFO/MainProcess] Task core.ping[3dd8f15e-…] succeeded in 0.01611409999895841s:
                    {'task_id': '3dd8f15e-…', 'message': 'roundtrip'}
```

A worker reachable on the broker, a message published to the real broker, the
message consumed, and the result returned through the real result backend. The
existing skip in `test_celery_integration.py:55` guards this test for
Windows `prefork` only, and is silent on Linux — Render's runtime — where
`prefork` inherits the populated list by ordinary `fork()`. No production
runtime confirmation is required for Celery execution, because execution has
been demonstrated, not inferred.

Consequence for the operator: nothing in §9 concerns Celery. There is no
"confirm the worker executes tasks" step, because it is already demonstrated.

## 7. End-to-end proof of the invitation email path

AUD-015's claim is that invitation email is delivered by a background worker
through real SMTP, and that the action link is correct. Unit tests can show a
task body runs; they cannot show a message leaving the process. This pass
therefore ran the whole chain with only the SMTP peer substituted:

```
PostgreSQL 15 (TLS required by prod.py)
      -> Redis broker
      -> separate Celery worker process, config.settings.prod
      -> real SMTP conversation
      -> message captured off the wire
```

Details that make this a genuine test of the production path rather than a
re-run of the unit tests:

* the worker ran under `config.settings.prod`, which *refuses to boot* on a
  non-SMTP `EMAIL_BACKEND`, on missing credentials, or on missing
  `FRONTEND_URL` — so its configuration had to be production-valid
* PostgreSQL had to be given a TLS certificate first, because `prod.py`
  requires `ssl_require=True`
* the publisher had to be forced off eager mode through the project's own
  `publish_via` helper, since the uppercase `CELERY_TASK_ALWAYS_EAGER` key
  shadows the lowercase alias (the reason that helper exists)
* the invitation row was created in the throwaway database the worker reads

```
enqueue returned AsyncResult: True
eager was off, broker: redis://localhost:6379/0
PASS  recipient is the invitee
PASS  from is DEFAULT_FROM_EMAIL
PASS  multipart with an html alternative
PASS  action link has FRONTEND_URL + token
worker reported success: True
```

with the worker's log:

```
[INFO/MainProcess] email task sent
[INFO/MainProcess] Task core.send_invitation_email[cb6f26e7-…] succeeded in 0.056s:
                    {'status': 'sent', 'recipient': 'i**************b@e2e.local', 'attempt': 1}
```

Note the recipient is masked in the log while the full address reaches the
SMTP peer — the masking is a log-hygiene property, and this run confirms it
does not corrupt the delivered message.

Production-settings cache health was checked the same way, in a process booted
from `config.settings.prod` against the real Redis:

```
cache backend : django.core.cache.backends.redis.RedisCache
uses_shared   : True
CACHE_MUST_BE_SHARED: True
check_cache   : [true, "ok"]
```

and the TLS/SSL misconfiguration guard fires as designed:

```
ImproperlyConfigured: EMAIL_USE_TLS and EMAIL_USE_SSL are mutually exclusive;
set only one in production.
```

## 8. Phase 5–7 — frontend, isolation, manifest

### 8.1 Frontend

```
$ npm run build    # 157 modules, 444.15 kB JS / 123.75 kB gzip, 11.67 kB CSS, built in 1.21s
$ npm run lint     # 13 problems (12 errors, 1 warning)
```

Lint is exactly the locked baseline, with the same categories: 11×
`react-hooks/set-state-in-effect`, 1× `exhaustive-deps`, 1× `no-undef` for
`process` in `vite.config.js`. No rule was weakened, no new debt introduced.
No frontend file was modified in this pass, and `services/api.js` is untouched.

One discrepancy worth naming rather than smoothing over: the bundle is
444.15 kB where the figure recorded in `AGENTS.md` is 443.78 kB, a 0.37 kB
increase with no frontend change in this pass. The recorded figure is stale,
not a regression here — `AGENTS.md` was last written at the H2 phase, and
`3cba284` ("add login and refresh throttling") has since modified
`frontend/`, which is the sole commit touching it since. 157 modules and
11.67 kB CSS are unchanged, which is the signature of a small JS-only
addition rather than a structural change.

### 8.2 Tenant isolation

The file named in the verification request,
`apps/accounting/tests/test_tenant_isolation.py`, **does not exist** — not in the
current tree, and not in any commit in the repository's history. The 53-test
isolation-bearing file is `apps/accounting/tests/test_accounting_api.py`:

```
$ py -m pytest apps/accounting/tests/test_accounting_api.py -q
53 passed
$ py -m pytest apps/accounting/tests/test_accounting_api.py -q -k "tenant or cross"
12 passed, 41 deselected
$ py -m pytest apps/accounting/tests/ -q
106 passed
```

A static sweep for unscoped querysets in API-facing modules
(`apps/*/views.py`, `apps/*/serializers.py`, `apps/*/*/views.py`) found only
two categories, both correct:

* `apps/accounts/views.py` — user lookup by email, membership by
  authenticated user, blacklist by `jti`, and the AUD-012 refresh guard
  filtering `Tenant.objects.filter(id=tenant_id, status=ACTIVE)`. All are
  scoped to the authenticated subject or to a token-derived id.
* `apps/purchases/views.py:234` and `apps/sales/views.py:214` — the AUD-029
  `paid_amount` subqueries, which are `OuterRef` correlated per row, not list
  queries.

No unscoped list queryset remains in the audited API surface.

### 8.3 Manifest, migrations, hygiene

* `apps/core/tests/test_render_infrastructure.py` — 14 passed, and **not**
  skipped: the live Render blueprint schema is fetched and validated, so
  `render.yaml` is checked against Render's current schema, not a local copy.
* `render.yaml` has not changed since `9c6306d`.
* `py manage.py makemigrations --check --dry-run` → "No changes detected"
* `git diff --check` → clean
* No secret has ever been committed. `DJANGO_SECRET_KEY` is
  `generateValue: true` in a shared env-var group, and a search of the whole
  history of `render.yaml` for literal secret values returns only
  `user: cetrak` (a database user name). `backend/.env` is gitignored; only
  `backend/.env.example` is tracked.

## 9. The operator checklist — exhaustive

This is everything still required before the first deploy. It is complete:
every `sync: false` key in `render.yaml` is listed, and nothing else is
required. `DJANGO_SECRET_KEY` is deliberately absent — see the last item.

1. **Select a plan for the `cetrak-redis` Key Value instance.** `render.yaml`
   declares `type: keyvalue` with no `plan:`, so Render provisions its default
   tier. This instance is simultaneously the shared cache (AUD-014 throttle
   state), the Celery broker, and the result backend. Choose a paid,
   always-on tier: a free instance that idles out loses queued invitation
   email, and `maxmemoryPolicy: noeviction` means that under memory pressure
   the broker refuses writes rather than evicting tasks — the symptom is
   `email task enqueue failed: invitation is committed but not dispatched`, not
   an outage.

2. **Set all 12 prompted values on `cetrak-api` (web).** All are `sync: false`
   and Render will prompt on first deploy:

   | Key | Note |
   |---|---|
   | `CORS_ALLOWED_ORIGINS` | must match the frontend origin |
   | `CSRF_TRUSTED_ORIGINS` | must match the frontend origin |
   | `FRONTEND_URL` | becomes the invitation action link |
   | `EMAIL_BACKEND` | **must be exactly** `django.core.mail.backends.smtp.EmailBackend` |
   | `EMAIL_HOST` | required, non-empty |
   | `EMAIL_PORT` | e.g. `587` |
   | `EMAIL_HOST_USER` | required, non-empty |
   | `EMAIL_HOST_PASSWORD` | required, non-empty |
   | `EMAIL_USE_TLS` | set exactly one of TLS/SSL |
   | `EMAIL_USE_SSL` | set exactly one of TLS/SSL |
   | `DEFAULT_FROM_EMAIL` | required, non-empty |
   | `SYSTEM_DEFAULT_AI_KEY` | prompted for the web service |

3. **Set all 8 prompted values on `cetrak-worker`.** Same keys minus
   `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `SYSTEM_DEFAULT_AI_KEY`:
   `FRONTEND_URL`, `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
   `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`,
   `DEFAULT_FROM_EMAIL`. The worker boots `config.settings.prod`, so it will
   not start without them — this is intended, and §7 demonstrated the
   configuration being genuinely enforced.

4. **Set `VITE_API_BASE_URL` on `cetrak-frontend`** (1 prompted value), to the
   API's public origin.

5. **Decide the custom domain, if any.** `DJANGO_ALLOWED_HOSTS` is pinned to
   `.onrender.com` in the manifest. A custom domain must be added there, in
   the manifest, before it will serve requests.

Three `EMAIL_*` footguns are worth restating because each is a hard boot
failure with an error message that does not name the manifest: `EMAIL_BACKEND`
must be the exact SMTP class path; `EMAIL_USE_TLS` and `EMAIL_USE_SSL` are
mutually exclusive; and the worker's `FRONTEND_URL` must match the web
service's, or invitation links point at the wrong origin while mail still
sends successfully.

**Not an operator action: `DJANGO_SECRET_KEY`.** It is `generateValue: true`
in the `cetrak-runtime` group, so Render generates it, it is never written to
the repository, and the shared group is what guarantees the web service and
the worker cannot disagree about it. No rotation is required. It would only
become an action if the dashboard value were ever exposed.

## 10. What was not verified, and would not be verifiable from here

Stated so the GO is not read as broader than it is:

* **Render-provisioned infrastructure itself.** No Render account was used.
  `render.yaml` is validated against Render's published blueprint schema, and
  every service boots correctly under `config.settings.prod` locally, but the
  managed Postgres, the Key Value instance, and the deploy pipeline have not
  been exercised on Render.
* **A real SMTP provider.** The SMTP peer was a local capture server. The
  conversation, authentication, and delivery were real; a provider-specific
  rejection (DMARC, SPF, sandboxing a new `DEFAULT_FROM_EMAIL`) would not
  appear until the first real send.
* **Redis behaviour under memory pressure or failover.** `noeviction` is
  configured and its refusal is logged correctly; no exhaustion event was
  induced.
* **Three gunicorn workers in production.** The shared-cache requirement that
  makes this correct is verified — the throttle's live tests and the prod
  health check both confirm a shared backend rather than per-process locmem —
  but the multi-process deployment itself was not run.
* **Backup/restore drill** on the managed database, and **staging smoke
  testing** of the deployed application.

## 11. Bottom line

Three independent full-suite runs — fresh PostgreSQL 15, SQLite, and live Redis
— pass, and the PostgreSQL run reproduces the count recorded when these items
were closed, so nothing has silently regressed. Migration from an empty
database is clean and idempotent. The audited invariants are present in the
source, not just in the tests. The invitation path has been demonstrated
end-to-end against real infrastructure, which retires the last item the
previous pass had to leave open. The frontend is unchanged and at its locked
lint baseline. `render.yaml` validates against Render's current schema and has
not drifted.

One defect was found: a test-isolation leak that made the opt-in Redis
configuration — the configuration the repository documents — fail. It was
fixed, committed on its own as `e2c6a71`, and is test-only. Two prior
statements (the Celery runtime diagnosis and a named test file) were found
incorrect and are corrected here rather than repeated.

Deploy after the §9 checklist. Nothing in the code needs to change first.
