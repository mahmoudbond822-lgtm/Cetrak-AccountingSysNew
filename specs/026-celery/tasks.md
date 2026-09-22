# AUD-026 — Celery Background Task Foundation: Tasks

Each task is independently verifiable. Status reflects the implementation session.

## Settings

- [x] T1. `base.py` declares env-driven `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`
      with local defaults only. Verify: settings load; no credential in URL; not `None`.
- [x] T2. `base.py` declares JSON task serializer, JSON result serializer, JSON-only
      accepted content. Verify: settings assertions in test.
- [x] T3. `base.py` sets `CELERY_TIMEZONE = TIME_ZONE` and `CELERY_ENABLE_UTC = True`.
      Verify: equals Django `TIME_ZONE` ("UTC").
- [x] T4. `base.py` sets `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True`.
      Verify: settings assertion; no Celery deprecation warning on worker config load.
- [x] T5. `dev.py` redundant `CELERY_*` broker/result override lines removed (single
      source of truth in `base.py`). Verify: `grep -n CELERY config/settings/dev.py` → none.

## Test-mode isolation

- [x] T6. `test.py` sets `CELERY_TASK_ALWAYS_EAGER = True`.
- [x] T7. `test.py` sets `CELERY_TASK_EAGER_PROPAGATES = True` (failures propagate, not
      swallowed).
- [x] T8. A test proves `config.settings.base` (→ prod/dev) does **not** enable eager
      mode — eager cannot leak into production.

## Task

- [x] T9. `apps/core/tasks.py` defines `ping` registered as `core.ping` (idempotent,
      no DB/request/session, no credentials, JSON-safe return).
- [x] T10. Dead `apps/accounts/tasks.py` re-export removed.
      Verify: file absent; nothing referenced it.

## Tests (apps/core/tests/test_celery.py)

- [x] T11. Celery app imports and is configured from Django settings.
- [x] T12. Broker/result settings present, env-driven, credential-free.
- [x] T13. JSON-only serializers + accepted content; `pickle` not in accepted content.
- [x] T14. Timezone consistency (`CELERY_TIMEZONE == TIME_ZONE`).
- [x] T15. Eager mode + eager propagation asserted under test settings.
- [x] T16. `core.ping` registered by autodiscovery; `.delay()` returns expected payload
      under eager mode.
- [x] T17. Task exception propagates under eager mode (deterministic failure behavior).

## Integration (opt-in)

- [x] T18. `apps/core/tests/test_celery_integration.py` runs a real broker/worker
      round-trip **only** when `CETRAK_CELERY_INTEGRATION=1`; default suite skips it
      (no Redis dependency).

## Environment docs

- [x] T19. `backend/.env.example` committed documenting `CELERY_BROKER_URL`,
      `CELERY_RESULT_BACKEND`, `REDIS_URL` with local values; no secrets.
- [x] T20. `backend/.env` remains gitignored and uncommitted (no secret in diff).

## Verification

- [x] T21. Targeted: `py -m pytest apps/core/tests/test_celery.py
      apps/core/tests/test_celery_integration.py -q` passes.
- [x] T22. Full backend: `py -m pytest apps/ -q` passes (no auth/accounting/tenant
      regressions).
- [x] T23. Migrations: `py manage.py makemigrations --check --dry-run` → no changes.
- [x] T24. `git status --short` — only AUD-026 files present.

## Spec-Kit

- [x] T25. `specs/026-celery/{spec.md,plan.md,tasks.md}` present.
- [x] T26. `report.md` written summarizing implementation, security review, and results.
