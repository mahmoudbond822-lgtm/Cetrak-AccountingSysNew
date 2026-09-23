# AUD-015 — Production Email Delivery (Implementation Report)

- **Item**: AUD-015 (P2) — "Invitations never emailed: token returned in API only; no email transport anywhere."
- **Status**: **CLOSED**
- **Substrate**: Celery foundation (AUD-026) — first real business consumer.
- **Branch**: `014-auto-customer-code`; **HEAD**: `cc7e0b6` (baseline).
- **Date**: 2026-09-23
- **Constraint honored**: only AUD-015 was implemented. No other audit (AUD-010/011/012/014/029) or product feature was touched. Frontend, emall API payloads, response contracts, and AuthService behavior unchanged (`services/api.js` untouched). One pre-existing test (`RefreshCookieTests.test_prod_settings_force_secure_refresh_cookie`) was updated to supply the now-required production email env vars; no test was weakened.

## 1. Summary

Cetrak created invitations but never delivered them — the token existed only in the
serializer response. With the AUD-026 Celery substrate in place, email delivery is
now a first-class async path:

- Env-driven Django email settings with safe per-environment defaults
  (console for dev, locmem for tests) and a **fail-fast production validation**
  that refuses to boot with a development backend or a missing SMTP value.
- A single Celery task (`core.send_invitation_email`) that renders server-templated
  HTML + plain-text messages and sends them through the configured SMTP relay with
  bounded exponential-retry backoff, permanent-error classification, and an
  idempotent re-read of invitation state at execution time.
- Transaction-safe dispatch: invitations are only emailed after the enclosing
  transaction commits (`transaction.on_commit`); a rollback produces no email.
- HTML/plain-text invitation templates (Cetrak-branded, auto-escaped, token-bearing
  action link), a recipient-redaction helper for safe logging, and zero tokens,
  credentials, or full recipient addresses in any log output.

## 2. What Changed

New files:

- `backend/apps/core/mail.py` — redaction, action-URL builder, message builder
  (`EmailMultiAlternatives`), async enqueue seam.
- `backend/apps/core/templates/email/invitation_email.html` / `.txt` — invite emails.
- `backend/apps/core/tests/test_email_config.py` — settings / prod-validation tests.
- `backend/apps/core/tests/test_email_generation.py` — redaction / URL / template tests.
- `backend/apps/core/tests/test_email_task.py` — task success, retry, skip, security.
- `backend/apps/core/tests/test_email_transaction.py` — on_commit + rollback wiring.
- `docs/audits/AUD-015-implementation-report.md` — this report.

Modified files:

- `backend/apps/core/tasks.py` — added `core.send_invitation_email` + error taxonomy.
- `backend/apps/accounts/views.py` — `transaction.on_commit` → `enqueue_invitation_email`.
- `backend/config/settings/base.py` — env-driven `EMAIL_*` + `FRONTEND_URL` (console default).
- `backend/config/settings/test.py` — `EMAIL_BACKEND = locmem`.
- `backend/config/settings/prod.py` — fail-fast SMTP-only validation block.
- `backend/.env.example` — documented email + `FRONTEND_URL` vars.
- `render.yaml` — `EMAIL_*` + `FRONTEND_URL` declared (`sync: false`, no defaults).
- `backend/apps/accounts/tests/test_refresh_cookie_csrf.py` — supplies email env vars
  in the existing prod-import drill test.

## 3. Why this shape

1. **Only invitations need email.** Spec 002-team-invitations US1 is the only flow in
   the product that requires email delivery. Password reset, security notices, and
   tenant notifications were grep-verified to not exist; none were invented.
2. **Services layer stays the seam** (constitution §combined). `mail.py` owns message
   construction from committed state; the view only registers a deferred dispatch;
   the task owns transport + retries. No business logic moved into the view.
3. **Async on the AUD-026 substrate** (constitution §VII): HTTP request handling is
   never blocked by SMTP; the worker retries on its own schedule.

## 4. Configuration

`base.py` (env-driven, dev defaults):

| Setting | Default (non‑prod) |
|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` |
| `EMAIL_HOST` / `EMAIL_PORT` | `""` / `587` |
| `EMAIL_HOST_USER` / `PASSWORD` | `""` / `""` |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | `false` / `false` |
| `DEFAULT_FROM_EMAIL` | `Cetrak <noreply@cetrak.local>` |
| `FRONTEND_URL` | `http://localhost:3000` |

`test.py` overrides `EMAIL_BACKEND` → `locmem` (outbox assertions, no network).

`prod.py` (fail-fast, aligned with the existing `DJANGO_SECRET_KEY` check):

- MUST be `django.core.mail.backends.smtp.EmailBackend` — dev backends rejected.
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`,
  `FRONTEND_URL` MUST be provided via env.
- `EMAIL_USE_TLS` and `EMAIL_USE_SSL` are mutually exclusive.
- Error messages reference variable names, never values (verified: the SMTP password
  value does not appear in any `ImproperlyConfigured` message).

## 5. Delivery pipeline

```
POST /tenants/invitations/  (admin)
  → InvitationService.create_invitation()   (atomic, existing)
  → transaction.on_commit(enqueue_invitation_email(invitation.id))
      → core.send_invitation_email.delay(uuid)     (Celery)
worker:
  re-read Invitation (select_related tenant)
  skip if missing / accepted / expired / cancelled
  build message from templates
  send via Django email backend (SMTP in prod)
  classify failure → retry | permanent_failure | FAILURE
```

### Idempotency (deliberate, explicit)

The task receives only the invitation PK and re-reads **current** state at execution
time. A worker retry can never resurrect an email for state that changed (accepted,
expired, cancelled) after enqueue. Cancelled invitations are deleted rows, so they
take the `missing` path and are never re-emailed. Documented limitation: retries are
**at-least-once** — a duplicate manual dispatch of the same still-pending invitation
would email twice; that is not something the retry policy itself can introduce.

## 6. Retry policy

| Outcome | Behavior |
|---|---|
| Transient (`SMTPConnectError`, `SMTPServerDisconnected`, `SMTPResponseException`, `socket.timeout`/`TimeoutError`, `ConnectionError`, `OSError`) | `self.retry` with `countdown = 60 * 2**retries` (60s, 120s, 240s), bounded by `max_retries = 3`; the final countdown is capped at the 3rd attempt. |
| Permanent (`SMTPAuthenticationError`, `SMTPRecipientsRefused`, `SMTPSenderRefused`, `SMTPDataError`) | Returned as a `permanent_failure` result — never retried, clearly surfaced. |
| Unexpected exception | Propagates → task `FAILURE` in the result backend (visible/alertable). |

First-retry countdown is guaranteed by Celery's `default_retry_delay = 60` and
explicitly verified: under eager mode the raised `celery.exceptions.Retry` carries
`when == 60` for `retries == 0`.

## 7. Transaction safety

- The enqueue runs inside `transaction.on_commit`, tied to the request's transaction.
- Verified end-to-end:
  - After a committed POST, exactly one email is delivered **only after** the
    `captureOnCommitCallbacks(execute=True)` block exits (i.e., nothing during the
    request, nothing partial).
  - In a rolled-back atomic block, `mail.outbox` stays empty and the invitation row
    does not exist — the callback is discarded with the savepoint.
- Because `Django TestCase` never fires `on_commit`, tests use Django 6's
  `TestCase.captureOnCommitCallbacks` context manager (the standalone
  `CaptureOnCommitCallbacks` class was removed in Django 6).

## 8. Security

- **No token in logs or audit data**: logs carry only `invitation_id` (UUID), a
  *redacted* recipient, `error_type`, `attempt`/`retry`, `kind`, `backend`, `status`.
  Verified with caplog: the invitation token, the SMTP password, and the full
  recipient address never appear in any emitted log record.
- **Template hardening**: messages render from server-controlled templates with
  `autoescape on`; user-controlled tenant names are escaped (verified with a
  `<script>` tenant name); no `|safe` anywhere; the plain-text body carries no HTML.
- **Secrets never committed**: settings read `EMAIL_HOST_PASSWORD` from env only;
  `.env.example` ships a placeholder; `render.yaml` declares `sync: false` with no
  default value.
- **Tenant isolation**: the task is keyed by an invitation UUID; all data is read
  from that invitation's own row/tenant. No new cross-tenant surface exists.
- **PII-conscious logging**: recipient addresses are masked (`i*****d@example.com`)
  in every log line; only the invitation row itself keeps the address.
- **No API/contract change**: the invitation serializer still does not expose the
  token; endpoint, payloads, statuses, and tenant/permission behavior are unchanged;
  `services/api.js` untouched; the frontend toast "Invitation sent to {email}"
  remained accurate and was therefore left as-is.

## 9. Verification

- New tests: **51** (config 19, generation 10, task 14, transaction 4, + counted as
  in-file params).
- Full backend suite: **506 passed, 2 skipped** (baseline 455 passed / 2 skipped +
  51 new; skips = 1 pre-existing + 1 opt-in Redis integration round-trip).
- Targeted pre-change baseline re-run for the touched areas (test_celery +
  test_team_api): 45 passed.
- Migrations: `makemigrations --check --dry-run` → **No changes detected** (no model
  changes; email is transport only).
- Frontend build: clean (156 modules, 438.19 kB JS / 122.48 kB gzip, 11.67 kB CSS).
  Frontend was not modified.
- Frontend lint: unchanged at the locked baseline — **13 problems (12 errors,
  1 warning)**, all pre-existing categories; zero new debt, no rules weakened, no
  frontend files touched.

### Test coverage map

| Concern | Test |
|---|---|
| Base/dev defaults, test locmem | `TestEmailConfigDefaults` |
| Prod fail-fast: non-SMTP backend, missing vars, TLS+SSL, no secret leak | `TestProdEmailConfig` |
| Redaction values | `TestRedactEmail` |
| Action URL from `FRONTEND_URL` (trailing-slash safe) | `TestActionUrl` |
| Subject/recipient/alternatives, token link in both bodies | `TestBuildInvitationMessage` |
| HTML escaping of tenant name; text body free of HTML | `TestBuildInvitationMessage` |
| Task registration name + `max_retries=3` + backoff values | `TestTaskRegistration` |
| Success metadata + real outbox content | `TestTaskExecution` |
| Skip on missing / accepted / expired / cancelled | `TestTaskExecution` |
| Transient → `Retry` with countdown; permanent → no retry; unexpected → propagate | `TestTaskFailureClassification` |
| No token/credential/full-recipient in logs (caplog) | `TestTaskLoggingSecurity` |
| Enqueue returns a usable `AsyncResult` | `TestEnqueue` |
| Email only after commit; rollback sends nothing; rejected invite sends nothing | `TestInvitationEmailDispatchTests` |

## 10. Known limitations (documented, not defects)

- **At-least-once delivery** with bounded retries: a retry after a successful SMTP
  handoff but a lost handshake could theoretically double-send in a real broker;
  the state re-read prevents sending for revoked invitations but cannot deduplicate
  two accepted deliveries to a still-pending invite. Delivery dedup (e.g., sending
  nonce) was deliberately out of scope for this P2.
- **No email for password reset / account notifications** — those features do not
  exist; AUD-015 remains the only email path by product design.
- **Human tab/branding still worth a spot-check** in a real browser/mail client;
  content verified via tests, not a live SMTP round-trip (gated behind
  `CETRAK_CELERY_INTEGRATION=1` + real broker, as with AUD-026).

## 11. Deployment notes

1. Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`,
   `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`,
   `DEFAULT_FROM_EMAIL`, and `FRONTEND_URL` in the environment (Render dashboard or
   blueprint sync — all declared `sync: false`).
2. `FRONTEND_URL` must be the public app origin (used for `/register?token=...` links).
3. No migration to run; the worker service (`cetrak-worker`) picks up the new task
   from the same code deploy.

## 12. Files

See §2 manifest. Reporting scorecard from the AUD-003 re-audit re-verified this
session: unchanged at **GO / READY (92/100)**, with AUD-015 moved from OPEN → CLOSED.