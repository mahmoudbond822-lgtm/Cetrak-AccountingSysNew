# PostgreSQL is the default test database in CI

**Status:** implemented, verified locally against `postgres:15-alpine`
**Scope:** CI configuration + test-settings plumbing + this note. No application
code, no migrations, no business logic, no production configuration
(`render.yaml` untouched), and no closed audit item was touched.

## The motivating incident

`apps/accounting/migrations/0005_decimal_exact_balance_check.py` installs an
exact-equality `CHECK` constraint through a `RunPython` migration that is a
**deliberate no-op on SQLite**. The suite therefore never executed that
constraint while it was SQLite-only, and the accounting domain shipped with a
database-enforced invariant that CI had never actually run.

The gap was not subtle once understood, and `AUD-030` had to compensate with
`apps/accounting/tests/test_decimal_exact_balance_constraint.py`, which calls
the migration functions against a *stand-in* schema editor so the PostgreSQL
branch is covered on any backend. That compensation is worth keeping — it is
what makes the suite portable — but it is a mock, and a mock is not the same
evidence as the constraint existing in a real database. There is a second
PostgreSQL-only behaviour in the suite as well:
`apps/inventory/tests/test_sales_inventory_api.py:290` skips its row-lock
serialization test unless `connection.vendor == "postgresql"`.

So: the default test database is now PostgreSQL, and SQLite remains a
deliberately separate, deliberately weaker gate.

## What changed

### Before

There was no CI at all — no `.github/` directory, no workflow, no pipeline. The
backend selected by CI was therefore not a matter of configuration; there was
nothing running. The suite was SQLite-only everywhere by default, because
`config/settings/test.py` inferred SQLite whenever the `POSTGRES_*` variables
were absent, and nothing in the repository set them for a test run.

### After

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | **new.** Two jobs: `test-postgres` (the default gate) and `test-sqlite` (the fast gate) |
| `backend/config/settings/test.py` | the backend is now *declared* via `CETRAK_TEST_DB`; `postgres` fails loudly instead of falling back to SQLite. The historical inference is preserved verbatim when the variable is unset |
| `backend/apps/core/tests/test_test_database_selection.py` | **new.** 30 tests covering the selector, including the two failure modes |
| `docs/audits/ci-postgresql-default.md` | **new.** this note |

### The `test-postgres` job

Service `postgres:15-alpine` — the same image and major version as
`infra/docker-compose.yml` and as every manual verification run, so a CI
failure is reproducible locally with the same image. The job waits for
`pg_isready` via the service health check before any step runs, because the
entrypoint initialises the cluster before it accepts connections. It then:

1. installs `requirements/dev.txt` on Python `3.11.9` (from `backend/runtime.txt`,
   so CI cannot drift from the deployed runtime)
2. prints the resolved engine, so the CI log records which database was used
3. runs `makemigrations --check --dry-run` **against PostgreSQL** — a
   migration can be engine-specific, so checking it on the wrong backend does
   not answer the question
4. runs `migrate --noinput` against an **empty** database, then runs it again to
   prove idempotency. pytest-django would create a separate `test_cetrak` and
   would prove neither property
5. runs `python -m pytest apps/ -q`

### The `test-sqlite` job

No service, `CETRAK_TEST_DB=sqlite`, the same migration check, then the suite.
It is kept because in-memory SQLite is the right engine for a tight
edit/run loop, and because a regression that is not database-specific should be
caught by the cheapest job available. It is **not** allowed to stand in for the
PostgreSQL job: `CETRAK_TEST_DB=sqlite` is declared, so this job stays on
SQLite even if the runner ever provides `POSTGRES_*` variables.

### Why the explicit selector rather than only setting env vars

Setting the four `POSTGRES_*` variables in the workflow would have been enough
to point CI at PostgreSQL, and it would have required no change to
`test.py`. It was rejected because the original inference makes a
misconfiguration *silent*: drop or mistype one variable and the job goes green
while quietly testing SQLite — the same miss as `0005`, triggered by config
instead of by default. `CETRAK_TEST_DB=postgres` turns that into a build
failure that names the missing variable:

```
ImproperlyConfigured: CETRAK_TEST_DB=postgres requires POSTGRES_HOST to be
set; refusing to fall back to SQLite, because a suite that silently skips the
database-specific migrations is not a pass.
```

Verified: that path exits `1`, so GitHub Actions fails the job.

## How to run SQLite locally for fast iteration

The default. With no environment set, the historical inference applies and you
get in-memory SQLite:

```bash
cd backend
python -m pytest apps/ -q
```

To be explicit (useful in a shell that has PostgreSQL variables exported):

```bash
cd backend
CETRAK_TEST_DB=sqlite python -m pytest apps/ -q
```

To run against PostgreSQL locally — the same way CI does, and the way to
reproduce a CI-only failure:

```bash
docker compose -f infra/docker-compose.yml up -d db
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test CETRAK_TEST_DB=postgres \
  POSTGRES_DB=cetrak POSTGRES_USER=cetrak POSTGRES_PASSWORD=cetrak \
  POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 \
  python -m pytest apps/ -q
```

`CETRAK_TEST_DB` is optional when you export all four `POSTGRES_*` variables —
that inference is unchanged — but setting it is recommended, because it turns a
typo into an error instead of an unexpected SQLite run.

On PowerShell:

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE="config.settings.test"
$env:CETRAK_TEST_DB="postgres"
$env:POSTGRES_DB="cetrak"; $env:POSTGRES_USER="cetrak"; $env:POSTGRES_PASSWORD="cetrak"
$env:POSTGRES_HOST="127.0.0.1"; $env:POSTGRES_PORT="5432"
py -m pytest apps/ -q
```

The opt-in suites are unchanged and still work: `CETRAK_REDIS_INTEGRATION=1`
(plus `REDIS_URL`) for the live-Redis tests, `CETRAK_CELERY_INTEGRATION=1` for
the broker round-trip.

## Verification

Run locally against a fresh `postgres:15-alpine` container, replicating each
job's step sequence and environment exactly. Interpreter was the machine's
Python 3.14.3, not CI's 3.11.9 — see the caveat below.

| | PostgreSQL 15 job | SQLite job |
|---|---|---|
| `makemigrations --check --dry-run` | "No changes detected", exit 0 | "No changes detected", exit 0 |
| `migrate` from an empty database | 45 applied, exit 0 (9.8 s) | n/a |
| `migrate` again | "No migrations to apply", exit 0 | n/a |
| Suite | **661 passed, 10 skipped, 25 subtests** | **660 passed, 11 skipped, 25 subtests** |
| Wall clock | 12:48 | 10:21 |

### Count reconciliation

The pre-change figures at this commit were 631 passed / 10 skipped on
PostgreSQL and 630 passed / 11 skipped on SQLite. The deltas are **entirely**
the 30 new tests in `test_test_database_selection.py`, and nothing else moved:

| | before | after | delta |
|---|---|---|---|
| PostgreSQL passed | 631 | 661 | +30 |
| PostgreSQL skipped | 10 | 10 | — |
| SQLite passed | 630 | 660 | +30 |
| SQLite skipped | 11 | 11 | — |
| Subtests | 25 | 25 | — |

No previously passing test changed state, no skip count moved, and the subtest
count is deliberately unchanged — the new tests use `pytest.mark.parametrize`,
which is the style of the neighbouring `test_email_config.py` and
`test_render_infrastructure.py`, precisely so that the reported subtest figure
does not drift for a change that adds no subtests.

The remaining one-test difference between the two backends is the known
PostgreSQL-only row-lock test, which skips on SQLite.

### Other checks

* A pre-existing teardown warning appears on repeated PostgreSQL runs against
  the same server (`test_cetrak` is still connected when the drop is
  attempted). It is environmental, affects no assertion, and does not occur on
  a first run against a fresh cluster — which is what CI does. It was already
  observed and recorded in
  `docs/audits/final-production-readiness-verification-report.md`.
* A defect found *by the new tests during this work*, and fixed: the first
  version of the resolver returned a shared module-level dict for SQLite. Django
  mutates `settings.DATABASES` in place when creating the test database
  (rewriting `NAME` to `file:memorydb_default?mode=memory&cache=shared`), so
  the shared dict was corrupted for every later caller. It passed in isolation
  and failed only in a full-suite run — the exact failure shape a fast local
  loop never shows. Each call now returns a fresh dict, and
  `test_each_call_returns_an_independent_config` reproduces the original bug
  when the shared dict is reintroduced (verified: 2 failures, 30 passes).
* SQLite job immunity verified: with all four `POSTGRES_*` variables set *and*
  `CETRAK_TEST_DB=sqlite`, the resolved engine is `sqlite3` / `:memory:`.

## Caveats

* **The workflow has not run on GitHub Actions.** It was verified by executing
  each job's exact steps and environment locally against a real
  `postgres:15-alpine`. First push will be the first execution on the runner:
  `actions/checkout@v4`, `actions/setup-python@v5`, pip cache restore, and the
  service health check are standard but unexercised here.
* **Python 3.11.9 was not available locally**; verification ran on 3.14.3.
  `runtime.txt` pins 3.11.9 and the workflow requests that version, but the
  pins in `requirements/*.txt` are ranges, so a version-dependent install
  failure would only surface on the first CI run.
* **CI wall clock is the sum of both jobs** (roughly 25–30 minutes including
  install and cache warm-up) and they run in parallel. There was no previous CI
  to compare against, so this is a new cost, not an increase — and it is the
  cost of the PostgreSQL gate that did not exist before.
* No frontend job was added. The scope of this change is the test database, and
  `npm run build` / `npm run lint` remain manual. Worth a follow-up, not worth
  mixing into this commit.

## First GitHub Actions run

The workflow was pushed to a throwaway branch (`ci/first-run-verification`, at
`4eaf50b`) to exercise it on a real runner without touching `main`. It ran, and
it is **red**: both jobs fail during `pip install -r requirements/dev.txt`,
before any Django code is imported.

* Run: <https://github.com/mahmoudbond822-lgtm/Cetrak-AccountingSysNew/actions/runs/36458970580>
  (run id `36458970580`, event `push`, head `4eaf50b5f8cfa4b5083bb7bc6503ff15505442ed`)

| | `backend tests (PostgreSQL 15)` | `backend tests (SQLite)` |
|---|---|---|
| started | 17:33:36Z | 17:33:36Z |
| completed | 17:34:02Z | 17:33:53Z |
| wall clock | 26s | 17s |
| runner | `ubuntu-latest` | `ubuntu-latest` |
| conclusion | **failure** | **failure** |
| failing step | 5 — Install test dependencies | 4 — Install test dependencies |

Steps that completed before the failure, in both jobs: `actions/checkout@v4`
and `actions/setup-python@v5` both succeeded, and the PostgreSQL job's
`Initialize containers` step succeeded — so the `pg_isready` health check on
`postgres:15-alpine` passed. `setup-python` also proves that **3.11.9 is
available and installable on `ubuntu-latest`**: the version was requested and
provisioned successfully. The requested version is therefore not the problem,
and it does match `runtime.txt`.

The pip cache was a **miss**, which is expected and correct for a first run
there is no prior cache to restore. Because the job failed, the
`setup-python` post step was skipped, so no cache was written either.

Nothing downstream of the install ran, so this run produced **no** result for
`makemigrations --check`, `migrate` from zero, `migrate` again, or the test
counts. The 661/10 and 660/11 figures in the table above are still local-only
measurements and remain unconfirmed on a runner.

### Root cause

`backend/requirements/base.txt` requires `django>=6.0,<6.1`, and **every**
Django 6.0.x release declares `Requires-Python >=3.12` (PyPI metadata; the
project currently runs Django 6.0.4 on Python 3.14.3 locally).
`backend/runtime.txt` pins `python-3.11.9`, and both CI jobs request 3.11.9.
pip therefore cannot resolve the requirement at all:

```
ERROR: Ignored the following versions that require a different python version:
       6.0 Requires-Python >=3.12; 6.0.1 Requires-Python >=3.12; ...
ERROR: Could not find a version that satisfies the requirement django<6.1,>=6.0
ERROR: No matching distribution found for django<6.1,>=6.0
```

Reproduced locally with
`pip install --dry-run --python-version 3.11 --only-binary=:all: -r requirements/dev.txt`,
so the failure is deterministic and not a runner or network artifact.

### Caveat status

* **"The workflow has not run on GitHub Actions"** — **cleared, and answered in
  the negative.** The previously unexercised mechanics are now exercised and all
  of them work: checkout, `setup-python` 3.11.9 provisioning, the pip cache
  lookup, and the `pg_isready` service health check. The workflow does trigger
  and does start. What the run disproves is the *pass* expectation: it is red
  for a reason that has nothing to do with the test database, and the
  PostgreSQL/SQLite split remains unproven on a runner.
* **"Python 3.11.9 was not available locally … a version-dependent install
  failure would only surface on the first CI run"** — **still open, and it is
  exactly what happened.** The predicted failure materialised on the first run
  and it is not subtle: the dependency floor is Python 3.12, so 3.11.9 can
  never install this project's requirements.
* The wall-clock caveat cannot be revisited yet — the longest job ran 26
  seconds, so there is still no full-run timing to compare against 25–30
  minutes.

### Why this was not fixed here

Changing only `.github/workflows/ci.yml` to 3.12+ would turn CI green while
`backend/runtime.txt` still pins 3.11.9 — and `runtime.txt` is what Render
installs from, so the deployed build would fail at the same step. A green
check would then be hiding a broken deploy. The real fix is a one-line change to
`backend/runtime.txt` (raise the floor to 3.12+, keeping CI in step with it);
lowering the Django floor instead would be an application change. Both are
production-configuration edits and outside the scope of this verification, so
the run is reported red and left unfixed for an explicit decision.

### Fixes made

None. No workflow or CI-plumbing change was warranted, so there is no commit to
list beyond this documentation append.
