# Production Readiness & Architecture Audit — Cetrak Accounting System

- **Audit ID**: AUD-001
- **Date**: 2026-09-05
- **Auditor**: opencode (static, read-only) + targeted runtime verification (test suite, migrations check, frontend build/lint)
- **Scoped fork/commit**: `8d3902b` (working tree clean, nothing pushed/deployed)
- **Scope**: Features 001–012 as delivered in `backend/` (Django + DRF) and `frontend/` (React/Vite), versus `.specify/memory/constitution.md` and the Spec-Kit specs under `specs/001-*` … `specs/012-*`
- **Constraint honored**: strictly read-only. No code, migration, test, frontend, or config changes were made; no new feature (013) was created. The only artifact produced is this report.
- **Method**: full source review of backend apps (`core`, `accounts`, `accounting`, `sales`, `purchases`, `inventory`), all URL routes and their permission classes, serializers, services, models, migrations, settings (`base`/`dev`/`prod`/`test`), `config/urls.py`, `config/celery.py`; full frontend source review (`src/services`, `src/pages`, `src/components`); frontend review subagent; Spec-Kit compliance subagent; runtime verification commands (below).

---

## 1. Executive Summary

**Verdict: READY WITH CONDITIONS.**

The Cetrak backend implements a genuinely strong foundation for a multi-tenant accounting SaaS: tenant-scoped querysets, membership-checked permission classes on every app endpoint, balanced-and-immutable journal entries with a Postgres-level balance CHECK constraint, idempotent posting driven by unique `(tenant, reference)`, `select_for_update` row-locking for stock and overpayment prevention, hard rejection of negative stock, and a 274-test suite (1 Postgres-only skip) that exercises cross-tenant isolation across every app.

However, the system is **not production-ready today**. Several high-severity defects and constitutional gaps block go-live:

1. **Financial-report integrity bugs (P1)**: ledgers/reports include *unposted* journal entries (the Journal UI creates drafts it can never post), and the Balance Sheet clamps negative balances and net losses to zero, so a period with a net loss produces a **balance sheet that does not balance**.
2. **Session expiry bug (P1, frontend)**: the refresh interceptor drops the rotated refresh token — with `ROTATE_REFRESH_TOKENS=True` on the backend, every user is silently force-logged-out ~24–48 h after login.
3. **Data-loss bug (P1, frontend)**: invoice modal state is seeded once and never reset, so editing one invoice after another can overwrite the selected record with stale/blank data.
4. **Constitution §II violation (P1)**: no audit trail exists — user/role/account/settings/invoice changes leave no immutable history (only JEs and the StockMovement ledger are immutable by themselves). Constitution §VI/bcrypt, §VII/Celery (zero async tasks), §I (line tables without `tenant_id`) are also unmet or only partially met.
5. **Access-control gaps (P1–P2)**: `User.status == DISABLED` and `Tenant.status == SUSPENDED/CANCELLED` are not enforced on active sessions (disabled users keep API access for up to the 24 h token lifetime), and invite acceptance is not bound to the invited email address.

No P0 findings (no confirmed live cross-tenant data exposure, no confirmed double-spend/over-issue path, no exploitable remote code execution). Because none of the P1s affect the core, already-tested posting flows, the recommendation is **B** (fix the blocker list below before production go-live and before starting Feature 013), not C (an independent re-audit); the fix items are precisely scoped and mostly small.

---

## 2. Current Baseline

| Artefact | Result |
|---|---|
| Backend test suite | `py -m pytest apps/ -q` → **274 passed, 1 skipped** (17 s; the skip is the Postgres-only row-lock/constraint path) |
| Migrations drift | `py -m django makemigrations --check --dry-run` → **"No changes detected"** |
| Frontend production build | `npm run build` → **clean** (vite, 130 modules, 397 kB JS / 110 kB gzip) |
| Frontend lint | `npm run lint` → **16 problems (15 errors, 1 warning) — all pre-existing** (earlier feature files; the 012 tree is clean) |
| SCM state | Branch `012-inventory`; HEAD `8d3902b`; working tree clean; nothing pushed/deployed |
| Services | Postgres (default), Redis (cache/health only), Celery scaffold with **zero tasks**, no email transport configured |
| Password hashing | Django default **PBKDF2** (no `PASSWORD_HASHERS` override) — constitution §VI requires bcrypt |
| Accounts / audit | No audit-logging model or middleware anywhere in `backend/` |

---

## 3. Findings Summary

Severity scale: **P0** = critical / must remediate immediately; **P1** = high / blocks go-live; **P2** = medium / harden soon; **P3** = low / improve. Classification: **V** = confirmed vulnerability, **B** = confirmed bug, **A** = architectural risk, **T** = missing test, **R** = recommendation.

| ID | Sev | Area | Finding | Evidence | Classification |
|----|-----|------|---------|----------|----------------|
| AUD-001 | P1 | Reports | Ledger, trial balance, income statement, balance sheet include **unposted** manual journal entries | `accounting/services.py:118-123,166-175` no `posted=True` filter; UI never calls `postJournalEntry` (`JournalEntryForm.jsx:81`), button mislabeled "Post Entry" | B |
| AUD-002 | P1 | Reports | Balance sheet clamps every negative account balance and a net **loss** to 0 → report does **not balance** in a loss period | `accounting/services.py:270-300` (`bal = max(bal, 0)`; `net_income = max(..., 0)`) | B |
| AUD-003 | P1 | Frontend/auth | Refresh interceptor discards the rotated refresh token; backend blacklists the old one on every refresh → guaranteed force-logout ~24–48 h in | `api.js:26-35` (saves only `data.access`); `accounts/views.py:157-171`; `ROTATE_REFRESH_TOKENS=True` `settings/base.py:114` | B |
| AUD-004 | P1 | Frontend | Invoice modal seeds form state once and never resets (missing `key`), so editing record B after page load can **overwrite B with stale/blank data** | `InvoicesPage.jsx:162-168` vs `useState(seededForm(invoice))` `InvoiceForm.jsx:68`; payment/purchase pages use the `key` remount pattern | B |
| AUD-005 | P1 | Accounting | Float used for money in legacy accounting services (posting tolerance 0.001, running balances, report aggregates) — constitution §II deviation; drift risk at scale | `accounting/services.py:103-106,133-144,192-195,221-293`; `JournalEntrySerializer.validate` `:135-137` | A |
| AUD-006 | P1 | Audit trail | No audit log for user/role/account/invoice/settings changes; constitution §II "complete, immutable audit trail" unmet; system/regulatory gap | grep for `Audit`/`audit_log`/`history` → none; only `JournalEntry` + `StockMovement` are immutable by construction | V |
| AUD-007 | P1 | AuthZ | `User.status == DISABLED` not enforced on active sessions (valid access token keeps working ≤ 24 h); `Tenant.status == SUSPENDED/CANCELLED` never enforced anywhere in the request path | permissions files (`accounting/permissions.py`, `sales/permissions.py:4-41`, `purchases`, `inventory`) check membership only; `login`/`refresh` are the only status checks | A |
| AUD-008 | P2 | AuthN | Invitation acceptance is **not bound to the invited email**; a bearer invitation token can be redeemed by any account using the token | `accounts/services.py:150-162`; `accounts/views.py:44-58` create/accept by token without `email == invitation.email` check | V |
| AUD-009 | P2 | Frontend auth | Access + refresh tokens and role/tenant stored in `localStorage` (script-readable, no HttpOnly) — any XSS → full account takeover; no CSP anywhere | `api.js:8-18,49-58`; `index.html`; `LoginPage.jsx:22-28` | A |
| AUD-010 | P2 | Tenant isolation | Middleware prefers the **unverified** JWT `tenant_id` claim, then trusts client-supplied `X-Tenant-ID`; the middleware membership gate never runs for DRF (user authenticated later). Isolation currently holds only because every permission class re-checks membership — any future `IsAuthenticated`-only endpoint consuming `tenant_id` becomes an IDOR | `core/middleware.py:18-42,69-76`; DRF auth ordering | A |
| AUD-011 | P2 | Tenant isolation | Four line tables carry **no `tenant_id`** (BaseModel only) — constitution §I "every table" unmet; safe today only via joins to tenant-scoped parents | `accounting/models.py:84`, `sales/models.py:86`, `purchases/models.py:87`, `inventory/models.py:233` | A |
| AUD-012 | P2 | Tenant model | `TenantScopedModel.tenant` is `on_delete=CASCADE` — deleting a Tenant silently destroys all its accounting/inventory history (no archive/soft-delete path) | `core/models.py:22-25` | A |
| AUD-013 | P2 | Concurrency | Sales/purchase posting reads the draft invoice **without** `select_for_update`; correctness leans entirely on the unique `(tenant, reference)` JE idempotency (a duplicate POST is rejected but the loser returns a 400 "reference already exists") | `sales/services.py:292-361`, `purchases/services.py:295-394` (payments do lock: `sales/services.py:564-568,622-626`) | A |
| AUD-014 | P2 | AuthN/brute force | Only global DRF throttles (anon 20/h, user 100/h). 100 req/h per user is low enough to break a busy session and high enough that per-endpoint/login brute-force protection is weak; no dedicated login throttling, no lockout | `settings/base.py:97-105` | R |
| AUD-015 | P2 | AuthN flow | Invitation tokens are **never emailed** (no email transport, no task/queue) — the invitee cannot receive the token; flow is API-only/out-of-band | grep `send_mail`/`EmailMessage` → none; `accounts/services.py:123-137` returns token in the API response only | B |
| AUD-016 | P2 | Accounting | Post-time settings validation is asymmetric: purchases re-checks account **type** at posting, sales/inventory re-check only tenant + `is_active`; a changed account type after settings update would be posted against a wrong-type account | `purchases/services.py:270-281` vs `sales/services.py:262-273` vs `inventory/services.py:118-125` | A |
| AUD-017 | P2 | Frontend | Tenant drift after "switch": `/tenants/switch/` mints a new access but **not a new refresh**; a refresh issued while single-tenant re-copies the old `tenant_id` claim → post-refresh requests can land in the wrong workspace (UI shows switched tenant, token carries original) | `accounts/views.py:312-323`; `accounts/services.py:84-87`; `api.js` interceptor; `core/middleware.py:37-42` (JWT claim wins over header) | A |
| AUD-018 | P3 | Frontend | Most forms render `detail`/`non_field_errors` nowhere (only `PaymentForm`/`PurchasePaymentForm` do); backend `{"detail": …}` 400s look like silent no-ops | `InvoiceForm.jsx:136-139`, `AdjustmentForm`, `ProductModal`, `CustomerModal`, `VendorModal`, `CreateAccountModal` | B |
| AUD-019 | P3 | Accounting | `AccountViewSet.partial_update` swallows deactivation/service errors with `except ValueError: pass` → returns 200 while doing nothing (client believes success) | `accounting/views.py:66-77` | B |
| AUD-020 | P3 | Accounting | Dead code: `JournalEntryViewSet.create` (a `ReadOnlyModelViewSet` cannot route POST) creates an entry without setting `tenant_id` → latent NOT-NULL failure if ever routed | `accounting/views.py:92-109`; `accounting/urls.py:8` | B |
| AUD-021 | P3 | AuthZ | `me_view` PATCH exposes `status` and `email` as writable (self-disable self-DoS; disabled user could flip own status); serializer fields are all writable | `accounts/views.py:328-339`; `accounts/serializers.py:33-36` | V(weak) |
| AUD-022 | P3 | Accounts | `change_role`/`remove_member` accept a `requesting_user_id` they never use (a member can remove themselves if another Admin exists — allowed, but the guard is not least-privilege); also `remove_member` does not prevent self-removal | `accounts/services.py:179-208` | A |
| AUD-023 | P3 | Ops | Committed dev diagnostics `debug_account.py` / `check_user.py` (run against `config.settings.test`) are repo noise to remove/guard | `backend/debug_account.py`, `backend/check_user.py` (tracked) | R |
| AUD-024 | T | Tests | No tests for: concurrent double-payment/over-issue (row-lock races), balance-sheet **net-loss** case, disabled-user active-session, suspended-tenant access, refresh-rotation + blacklist reuse, invitation-email binding. Coverage is broad (cross-tenant matrix) but these specific invariants are untested | test tree (see §18) | T |
| AUD-025 | P2 | Constitution | §VI requires **bcrypt** — production/development use Django default PBKDF2 (test settings deliberately use MD5) | `settings/base.py:70-74` (no `PASSWORD_HASHERS`) | V |
| AUD-026 | P2 | Constitution | §VII requires heavyweight tasks **async via Celery** — Celery app + worker service exist but **zero tasks** are defined; nothing is async | `config/celery.py`, `accounts/tasks.py:1-3` (re-export only), grep `shared_task`/`.delay`/`apply_async` → none | A |
| AUD-027 | P3 | Frontend | `frontend/.env` declares `VITE_API_BASE_URL` but `api.js:4` reads `VITE_API_URL` → dead config, baseURL silently falls back to relative `/api/v1` | `api.js:3-6`; `frontend/.env` | B |
| AUD-028 | P3 | API | `GET /api/v1/health/` is unauthenticated and reports database+Redis reachability — acceptable for liveness, but be aware it leaks infra health to the internet | `config/urls.py:6-18` | R |
| AUD-029 | P3 | Performance | List endpoints have **no pagination** (accounts, invoices, customers, stock movements, ledger), and `paid_amount`/`outstanding_balance` are computed live per row (N+1) on every invoice/payment list/retrieve | `sales/views.py:183-191`, `sales/serializers.py:213-219`, no `PAGE...` settings | R |
| AUD-030 | P3 | Accounting | Postgres `balanced_entry_check` uses a **float** `ABS(SUM(debit)-SUM(credit)) < 0.01` tolerance; acceptable, but not Decimal-exact and Postgres-only (the application layer is the gate on SQLite/test) | `accounting/migrations/0002_balanced_entry_check.py:7-20` | R |

**Counts by severity:** P0 = 0 · P1 = 7 · P2 = 12 · P3 = 11 (incl. 1 missing-test item and 4 recommendations).

---

## 4. P0 Findings

No P0 findings.

No confirmed live cross-tenant data exposure, no confirmed double-spend/over-issue/double-posting path, and no exploitable injection/RCE were found. The two closest candidates were downgraded:

- **Unverified JWT claim parsing** (`core/middleware.py:18-42`) is not exploitable: the middleware only derives `request.tenant_id`; tokens are later signature-verified by `BlacklistCheckingJWTAuth`, and every endpoint's permission class re-checks membership for `request.tenant_id` (see AUD-010).
- **Refresh-token forgery** was investigated and ruled out: simplejwt verifies signatures in `RefreshToken.__init__`, and blacklisted `jti`s are re-checked at every refresh.

---

## 5. P1 Findings (block go-live)

### P1-1 · Unposted manual journal entries flow into ledgers and financial statements — AUD-001
- **What**: `JournalEntryService.create_entry` (`accounting/services.py:74-85`) creates entries with `posted=False` (model default, `accounting/models.py:36-41`). Posting is a separate explicit action (`accounting/views.py:129-145`).
- **Web UI**: `JournalEntryForm.jsx:81` calls only `createJournalEntry`; `postJournalEntry` (`accountingService.js:11`) is never called from any page — and the submit button is literally labeled "Post Entry" (`JournalEntryForm.jsx:180`).
- **Reports**: `LedgerService.get_ledger` (`:118-123`) and `ReportService._line_aggregation` (`:166-175`) do **not** filter `posted=True`. An accountant "creating" a manual entry therefore sees it in the ledger, trial balance, income statement, and balance sheet — as if posted — while the entry is still a draft and can never be corrected from the UI.
- **Impact**: financial statements can be misstated; the posted/unposted distinction is functionally meaningless from the UI.
- **Recommendation**: (a) surface a real "Post" action (or auto-post on create for the UI path while keeping the service contract), and (b) filter ledger/report queries to `entry__posted=True` (or include an explicit `include_unposted` flag behind permission). Add tests for "draft entries excluded from statements".

### P1-2 · Balance sheet breaks in a net-loss period — AUD-002
- **What**: `build_section` clamps each account's balance with `bal = max(bal, 0)` (`accounting/services.py:278`), and `net_income = max(total_revenue - total_expense, 0)` (`:293`). A period with a net loss produces `net_income = 0`, no negative retained-earnings line, so `total_liabilities_and_equity != total_assets`.
- **Impact**: the flagship statement does **not balance** whenever a company loses money — the exact situation where management most needs accurate reports.
- **Recommendation**: stop clamping; carry negative balances through (or add an explicit negative "Retained Earnings" / "Net Loss" line). Add a regression test with a loss period asserting `total_assets == total_liabilities + total_equity`.

### P1-3 · Rotated refresh token is dropped by the frontend → forced logout every ~24–48 h — AUD-003
- **What**: Backend blacklists every refresh on use (`accounts/views.py:157-162`, `ROTATE_REFRESH_TOKENS=True`). Frontend interceptor only persists `data.access` (`api.js:26-35`), discarding the new `data.refresh`.
- **Sequence**: at ~24 h the first silent refresh succeeds and blacklists the stored refresh → after the next 401 the *now-blacklisted* refresh is rejected → `localStorage.clear()` + redirect to `/login`. Remember-me (30-day) is moot. Concurrent 401s also fire multiple rotations with the same token (no single-flight), guaranteeing one of them fails.
- **Impact**: every user is silently logged out daily; in practice blocks all usage.
- **Recommendation**: persist `data.refresh`, dedupe refreshes with an in-flight promise, and only clear storage after a hard refresh failure.

### P1-4 · Invoice modal can overwrite the selected record with stale/blank data — AUD-004
- **What**: `InvoicesPage.jsx:162-168` renders `<InvoiceForm ... invoice={editing} />` with **no `key`**, so the component mounts once; `useState(seededForm(invoice))` (`InvoiceForm.jsx:68`) seeds on first mount only. Editing invoice A then invoice B on the same screen reuses the empty first-mount state while the save targets `editing.id` (B) → **record B overwritten with blank/stale fields**. The payment/purchase equivalent pages already use the `key`-remount pattern.
- **Impact**: silent data loss of invoices on sequential edits.
- **Recommendation**: apply the same `key={editing?.id}` remount (or a `useEffect` reset) used by `PaymentsPage.jsx:163`, `PurchaseInvoicesPage.jsx:163`, `PurchasePaymentsPage.jsx:166`.

### P1-5 · Float used for money in the accounting service layer — AUD-005
- **What**: `JournalEntryService.post_entry` sums `float(l.debit)` with a 0.001 balance tolerance (`accounting/services.py:103-106`); `LedgerService` accumulates running balances in float and biases totals with `float(...)` (`:133-144`); `ReportService` aggregates with float and formats `:.4f` (`:192-195,:221-293`); `JournalEntrySerializer.validate` also uses float (`:135-141`). Inventory/sales/purchases are Decimal-only.
- **Impact**: constitution §II deviation; float accumulation can drift over large ledgers, and the 0.001 tolerance can accept or reject an entry marginally. Stored values remain Decimal(19,4), so this is a computation/precision risk, not data corruption.
- **Recommendation**: convert the accounting service/serializer math to `Decimal` (quantized), with an exact balance check at 0 on a per-line basis; parity with the sales/purchases/inventory code.

### P1-6 · No audit trail — AUD-006
- **What**: grep for audit/history models, middleware, signals, or admin registrations across `backend/` returns nothing. User/role changes, account creation/deactivation, settings changes, draft→posted transitions, and CSRF/admin operations are not logged anywhere.
- **Impact**: constitution §II ("complete, immutable audit trail") is unmet; cannot answer "who changed what and when"; this is the largest leap toward production-grade accounting compliance (e.g., for auditability of financial records).
- **Recommendation**: introduce an append-only `AdminAuditLog` (tenant-id scope, actor, action, target, before/after JSON, timestamp, immutable) with a thin service helper called from the services layer for user/role/account/invoice/settings mutations; ship with the Feature 013-class work or a dedicated hardening feature.

### P1-7 · Disabled users / suspended tenants keep API access on active sessions — AUD-007
- **What**: `login` (blocked if `User.Status.DISABLED`, `accounts/services.py:53-54`) and `refresh` (`accounts/views.py:149-153`) are the only status checks. Every permission class verifies membership but never `user.status == ACTIVE` or `tenant.status == ACTIVE`, and the tenant claim is minted only after an active membership check at login. A user disabled at 09:00 keeps full API access until their access token expires (24 h); a tenant set SUSPENDED/CANCELLED (there is no endpoint, only DB) keeps every member working.
- **Impact**: terminations and tenant-hold are not actually enforced server-side; the frontend hides buttons but nothing else.
- **Recommendation**: in the permission classes (or the JWT authentication class), reject if `user.status != ACTIVE`; reject tenant-level requests when `tenant.status != ACTIVE` (resolve the tenant from `request.tenant_id` once per request to keep it cheap), including on `/tenants/switch/`.

---

## 6. Security

### Strengths
- **JWT everywhere**: single `BlacklistCheckingJWTAuth` default; every endpoint requires auth except the four ALLOWED_PATHS (`register/login/refresh/logout`) — constitution §III/§VI satisfied for auth.
- **Per-tenant permissions**: every app permission class (`sales/permissions.py`, `purchases/permissions.py`, `inventory/permissions.py`, `accounting/permissions.py`, `accounts/permissions.py`) checks `Membership` for `request.tenant_id` in addition to authentication, so `X-Tenant-ID` override cannot cross tenants (see AUD-010 for the residual).
- **Tenant-scoped field resolution**: all relational fields (`TenantScopedAccountField`, `TenantScopedCustomerField`, `TenantScopedVendorField`, `TenantScopedProductField`, `TenantScopedWarehouseField`, `TenantScopedPosted*Field`) restrict `queryset` to `request.tenant_id`; parent-account validation rejects cross-tenant parents and self-references (`accounting/serializers.py:29-54`).
- **Service-level double-checks**: posting re-verifies `tenant_id`-binding and `is_active` of configured accounts at posting time (`sales/services.py:262-273`, `purchases/services.py:260-281`, `inventory/services.py:118-125`).
- **Password rules enforced** (MinimumLength/Common/Numeric validators, `base.py:70-74`) and min-length-8 enforced in the register serializer.
- **Production security headers** (`prod.py`): HSTS, secure cookies, SSL redirect, `CORS_ALLOW_ALL_ORIGINS=False`, `ALLOWED_HOSTS` + `SECRET_KEY` hard-fail, `ssl_require=True` on the DB.

### Gaps
- **AUD-007** (disabled/suspended not enforced on sessions) — P1.
- **AUD-008** (invitation not bound to invited email) — P2. An admin inviting `boss@example.com` issues a bearer token usable by *any* account that holds it; because acceptance doesn't require `email == invitation.email`, a token holder can join the tenant under a different identity. Mitigated only by token secrecy.
- **AUD-021** (self-writable `status`/`email` via `me_view` PATCH) — P3: an attacker with a stolen account can change the email to lock the real owner out; a user can self-DISABLE.
- **AUD-014** (weak/global-only throttling) — P2: anon 20/h is a reasonable login brute-force brake, but user 100/h can starve a busy day and there is no per-endpoint or per-IP escalation, no account lockout.
- **AUD-015** (invitations never emailed) — P2: the token exists only in the API response; no delivery channel.
- **AUD-017** (tenant drift after switch) — P2.
- **AUD-009 / AUD-010** (client token storage; middleware trust model) — P2 hardening, below.
- `DEBUG=True` in `dev.py` with `CORS_ALLOW_ALL_ORIGINS=True` is acceptable for a dev environment but is a foot-gun if deployed; the compose file should target prod-like env.

---

## 7. Accounting Integrity

### Strengths
- **Balanced by construction**: the three automated posting paths create JEs where debit legs and credit legs are derived from the same quantized totals and always sum exactly (asset/revenue/COGS/inventory in sales; inventory/expense/VAT/AP in purchases; inventory/adjustments in adjustments — each pair from identical `consumed`/`value` values). The `AccountViewSet`-style free-form manual JE path is validated to balance in the serializer and service.
- **Defense in depth**: model-level `clean()` (`accounting/models.py:75-81`) + service float tolerance (`services.py:103-106`) + Postgres `balanced_entry_check` CHECK constraint (`migrations/0002`).
- **Immutable posted entries**: `JournalEntryViewSet` inhibits update/partial_update/destroy (`accounting/views.py:111-127`); posted flag is monotonic; invoice/payment/adjustment `posted_journal` links are `PROTECT`, and `Account` FKs on JE lines are `PROTECT`, so posted entries cannot be silently re-pointed or deleted.
- **Idempotency**: `UniqueConstraint("tenant","reference")` on JE (`accounting/models.py:47-52`) + wrap in the posting `transaction.atomic()` blocks → double-posting a document fails atomically with zero side effects.
- **No direct edits**: `http_method_names` on posting-related viewsets exclude PUT/DELETE for posted documents; the services enforce `status == DRAFT` before mutating.

### Gaps
- **AUD-001** (unposted entries in reports) — P1.
- **AUD-002** (net-loss balance sheet does not balance) — P1.
- **AUD-005** (float in legacy accounting math) — P1.
- **AUD-013** (invoice posting not row-locked; relies on idempotency instead) — P2. Payments *do* lock the invoice with `select_for_update` before recomputing outstanding (`sales/services.py:564-568,622-626`) — that is a correct CAN-SERIES-shielded design; the same pattern should be applied to draft posting so the DRAFT→POSTED transition itself is serialized (today a lost update is impossible thanks to the unique reference, but the 400 is opaque and a third concurrent transaction could observe a half-transitioned state at a non-REPEATABLE-READ isolation).
- **AUD-016** (post-time settings type checks asymmetric) — P2.
- **AUD-019/AUD-020** (view-layer error swallowing; dead createless-tenant code) — P3.
- **AUD-030** (float tolerance in the PG CHECK) — P3 recommendation.

---

## 8. Inventory Integrity

### Strengths
- **Moving weighted average** per `(tenant, product, warehouse)`; `value` is the authoritative aggregate, `moving_avg_cost = value/quantity` recomputed and quantized (`inventory/services.py:185-256`); test suite asserts `balance == Σ movements` (`test_stock_ledger_tie.py`).
- **Append-only ledger**: `StockMovement` rows are never updated/removed (no update/destroy paths; FKs `PROTECT`); the ledger tie-invariant is enforced and tested.
- **Negative stock hard-rejected**: `issue()` raises `ValueError("Insufficient stock.")` before any write (`:227-228`); posting is atomic, so a failing issue leaves zero artifacts.
- **Row-locking with a stable order**: `_get_balance` uses `select_for_update` and purchase/adjustment/sales posting iterate product lines sorted by `product_id` (`inventory/services.py:372`, `sales/services.py:324`, `purchases/services.py:326`) → consistent lock ordering avoids deadlock.
- **Decimal discipline**: inventory is entirely Decimal + `_quantize` with `ROUND_HALF_UP` (`:20-24`).
- **PROTECT FKs** on product/warehouse balances and movements; product deletion is blocked when movements exist (soft-deactivate instead, `inventory/views.py:83-104`).

### Gaps
- **AUD-013** applies to inventory only partly — the stock-path is already lock-ordered and atomic; the remaining gap is that draft posting of the *source invoice* isn't row-locked (see §7).
- No DB-level CHECK that `db_value == Σ movements` (enforced in app tests only) — acceptable for MVP, worth a validation script or periodic reconciliation job.
- Scaling: `StockMovement` history grows unboundedly with no retention/rollup strategy (P3, ops).

---

## 9. Sales / Purchases / Payments Lifecycle

### Strengths
- Draft → Posted state machines enforced in both services; posted invoices are write-protected at the API.
- **Overpayment prevention is race-safe**: `post_payment` locks the invoice row before recomputing outstanding and balances the JE from the same amount (`sales/services.py:551-607`, payable `609-674`); a concurrent second payment either waits or fails cleanly.
- Cross-tenant fields, customer/vendor `is_active` gates, non-negative price/quantity/tax-rate validation, discount ≤ subtotal, `due_date >= invoice_date` — all enforced at serializer and service layers.
- Unit-price-only credit (unit_price `>= 0`) — sales and purchases both allow 0-price lines but not negative; no negative stock effect possible even at zero price.
- Payments generalize cleanly across receivable/payable on a single `Payment` model with a CHECK constraint guaranteeing exactly one invoice reference (`sales/models.py:179-193`).

### Gaps
- **AUD-013** (draft posting not row-locked) — P2.
- **AUD-016** (settings type checks asymmetric at posting) — P2.
- **AUD-001** interplay: inventory COGS/stock effects are tied to posted invoices (correct); the manual-journal drafting (P1-1) is the only path where "not actually posted" state can bleed into the books.

---

## 10. Data & Migration Integrity

### Strengths
- Schema is deliberately simple and well-indexed: per-tenant unique constraints on `(tenant, number/code/sku/name/reference)` everywhere uniqueness matters; composite indexes on the hot filter paths (`(tenant,status)`, `(tenant,product,warehouse)`, `(tenant,vendor,invoice_date)`).
- Restrictive FK graph (`PROTECT` on journal links, customer/vendor/product/account references) prevents accidental orphaning of history.
- `makemigrations --check --dry-run` → clean; migration history is linear and includes the incremental 011/012 additive changes (`0002/0004` product FKs respectively).
- The one Postgres-specific gate (`0002_balanced_entry_check`) is correctly guarded by `schema_editor.connection.vendor != "postgresql"` so SQLite test runs don't fail.

### Gaps
- **AUD-011**: line tables without `tenant_id` (constitution §I) — see §12.
- **AUD-012**: `Tenant` FK `on_delete=CASCADE` (constitution-notable: deleting a tenant wipes everything). Consider `PROTECT` + explicit decommission workflow.
- Line tables (`SalesInvoiceLine`, `PurchaseInvoiceLine`, `StockAdjustmentLine`, `JournalEntryLine`) use `BaseModel` — their tenant identity is implicit through the parent; the DB cannot alone guarantee a line belongs to the same tenant as its parent.
- No DB-level CHECK for `quantity > 0` on invoice lines or non-negative amounts on JE lines (only app-layer; acceptable given services gate writes, but DB-level would be defense-in-depth).

---

## 11. API Security

- All endpoints authenticated by default (constitution §III) — the only AllowAny routes are the four auth paths and the health probe (AUD-028).
- JSON-only renderer, no browsable API in production.
- Consistent error shape via DRF `{"detail": ...}` / field-keyed errors (constitution §III satisfied in spirit).
- **Posting permissions**: `CanPostSalesInvoice` / `CanPostPurchaseInvoice` gate invoice & payment posting (Admin/Accountant); `CanManageInventory` gates adjustment posting (Admin/Accountant) — a documented deviation from the original "no separate CanPost" per plan, but Admin/Accountant alignment is consistent.
- **AUD-010** is the highest-priority API hardening item (avoid relying on "every permission class remembers to check membership"); make tenant-membership a shared permission base class or enforce in `BlacklistCheckingJWTAuth`.

---

## 12. Frontend Security & Correctness

See §3 (AUD-003, -004, -009, -017, -018, -027).

- **No XSS vectors found**: no `dangerouslySetInnerHTML`, `eval`, `innerHTML`; all data rendered through auto-escaping JSX. Table/report rendering (`Table.jsx`, `ReportTable.jsx`, `LedgerTable.jsx`) is safe.
- **Frontend RBAC is cosmetic only** (as documented): role/tenant from `localStorage` gates button visibility/dashboard; the backend enforces real permissions. No bypass found in the UI.
- **AUD-009 (P2)**: tokens + tenant in `localStorage` are readable by any script in the origin — the biggest frontend credential risk. Mitigations: short-lived in-memory access token + HttpOnly refresh cookie, and a strict Content-Security-Policy (addressed by AUD-027/CSP). There is currently **no CSP**.
- **AUD-003/AUD-017/AUD-018** are correctness bugs with user-visible impact; **AUD-004** is a data-loss bug.
- **AUD-027**: dead env var; `frontend/.env` is irrelevant (untracked, ignored) — harmless but confusing.
- No `.env.example`; recommend documenting the intended `VITE_API_URL`.

---

## 13. Audit Logging

**None exists** (AUD-006, P1). Beyond the constitution mandate, accounting-grade deployments should record: login/logout, tenant switch, invitation create/accept/cancel, member role changes/removal, account create/deactivate, settings changes, invoice/payment/adjustment posting, and admin actions — with actor, tenant, target, before/after, timestamp, and an append-only guarantee. This is the designated gap to close before production.

---

## 14. Transactions & Concurrency

- **Correct today**: posting (invoice/payment/adjustment) runs inside `transaction.atomic()` with JE idempotency; stock balance updates are row-locked with consistent ordering; overpayment/shared-balance read-modify-write is shielded by `select_for_update` on the invoice before outstanding recompute (`sales/services.py:564-568,622-626`).
- **Open items**: AUD-013 (invoice draft-row lock when posting), AUD-007 (membership/last-admin role-change race is `select_for_update`-protected in `change_role` — that one is fine), and the test gap for actual concurrent posting (AUD-024).

---

## 15. Performance

- Indexes are well-placed on filter, join, and order-by columns (constitution §VII satisfied for query design).
- **Not production-scale yet**: no pagination anywhere (AUD-029); per-row `PaymentService` calls inside serializers for `paid_amount`/`outstanding_balance` (N+1, `sales/serializers.py:213-219`); report/ledger float accumulation; no Celery tasks (AUD-026); global `user: 100/hour` throttle will cap heavy usage.
- The throttle is a double-edged control: it protects the API from abuse but will likely need raising or relaxing for normal multi-invoice days (AUD-014).

---

## 16. Financial Correctness

- Decimal storage everywhere (`DecimalField(19,4)`); VAT = `subtotal * rate/100` per line; discount = proportional allocation across product lines with a residual absorbed by the expense leg so the JE balances **exactly** (purchases `:304-356`); COGS = quantity × weighted-average at posting, with a balanced Dr COGS / Cr Inventory pair per line (sales `:323-353`).
- Manual-JE path is Decimal-stored with float validation (see P1-5).
- The float risk and the two report bugs (P1-1, P1-2) are the only financial-correctness defects found.

---

## 17. Test Coverage

**274 passing, 1 skipped.**

Strong areas:
- **Cross-tenant isolation matrix** (the strongest single suite): `test_cross_tenant_account_not_accessible`, `test_cross_tenant_parent_account_rejected`, `test_cross_tenant_no_side_effects`, `test_cross_tenant_object_lookup_404`, `test_cross_tenant_product_rejected_on_purchase`, `test_cross_tenant_cash_account`, ID-not-disclosed checks, same-SKU-across-tenants allowed, etc.
- **Inventory tie suite** (`test_stock_ledger_tie.py`) asserting `balance == Σ movements` and negative-stock rejection.
- Posting idempotency, overpayment rejection, discount-capped-subtotal, VAT rounding, immutable posted entries.
- Auth: register/login/logout/refresh team flows, invitation lifecycle, role-gating.

GAPS (AUD-024):
- No concurrency tests (parallel double-payment/double-post on the same invoice/stock balance).
- No balance-sheet **net-loss** assertion (P1-2 not caught).
- No disabled-user/suspended-tenant enforcement tests (gap behind P1-7).
- No refresh-rotation + blacklist-reuse test.
- No invitation-email-binding mismatch test (gap behind P2-008).
- No tests iterate the UI; the audit surfaced the P1-3/P1-4 frontend bugs because there is no UI test harness.

---

## 18. Spec-Kit Compliance (Features 001–012)

Reference: `.specify/memory/constitution.md` (v1.0.0, ratified 2026-06-13). §I multi-tenancy, §II accounting integrity + audit trail, §III REST/JWT, §IV services layer, §V AI-safety, §VI bcrypt, §VII async + indexes, §VIII MVP discipline.

| Feature | Deliverable status | Constitution notes |
|---|---|---|
| 001 Project Foundation | Implemented | §III/§IV/§VI(auth) satisfied; §VI bcrypt violated; §I partial (global identity tables lack tenant); §VII Celery scaffold only |
| 002 Team Invitations | Implemented | §I/§III/§IV satisfied; invite-not-emailed + not-email-bound (P2) |
| 003 Docker Compose Infra | Implemented | §VII partial: db/redis/api/frontend/**worker** services present, zero tasks |
| 004 Multi-tenancy Hardening | Implemented | §I app-level enforced; middleware gate only effective for session-admin (see AUD-010) |
| 005 Accounting Schema | Implemented | §II balanced (model + PG CHECK) + immutable; **no audit trail**; §I partial (`journalentryline` tenant-less) |
| 006 Accounting Frontend | Implemented | UI parity; AI suggestions deferred as-scoped (§V N/A) |
| 007 Accounting UI Refactor | Implemented | Non-constitutional; §IV analog upheld |
| 008 P0 Tenant Isolation | Implemented | §I satisfied for tenant tables (residual = AUD-010/011) |
| 009 Sales Cycle | Implemented | §I/§II/§III/§IV satisfied |
| 010 Payments & Receipts | Implemented | §I/§II/§III/§IV satisfied (Decimal, row-locked overpayment) |
| 011 Purchases & Payables | Implemented | §I/§II/§III/§IV satisfied; `purchase_invoiceline` tenant-less |
| 012 Inventory | Implemented | §I/§II(ledger)/§IV satisfied; §VII index-rich; transfers/batch/lot/returns deferred as scoped |

**Constitution deviations confirmed:**
1. **§VI bcrypt** → Django default PBKDF2 in dev/prod (test uses MD5 only; setting is test-only) — AUD-025.
2. **§VII async** → Celery configured, **zero tasks** — AUD-026.
3. **§II audit trail** → absent — AUD-006.
4. **§I "every table"** → 4 line tables tenant-less + 3 global identity tables (documented deviation) — AUD-011.
5. **§I middleware enforcement** → membership gate is a no-op for JWT clients (works only for session-auth admin) — AUD-010.
6. **§II float money** in legacy accounting services — AUD-005.
7. **§IV minor leaks** → register-invitation flow (bulk logic in `views.py:31-97`), refresh/blacklist (`:139-176`), tenant-switch token minting (`:287-325`), and silent `except ValueError: pass` in `accounting/views.py:66-77`; dominant pattern is services-layer-clean.
8. **§III error format** → compliant (uniform DRF errors; no custom normalizer needed).
9. **§V AI safety** → no AI feature in scope; N/A (not a violation).

---

## 19. Production Readiness Score

Weights: Security 25 · Accounting 25 · Data integrity 20 · Test confidence 15 · Performance 10 · Documentation/ops 5.

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Security | 25 | **15** | JWT + per-tenant membership everywhere, prod headers, hard-fail env config. Deduct: no disabled/suspended enforcement (P1), token-LS/CSP (P2), invite-not-email-bound (P2), throttling weakness (P2), no audit trail (P1, also counted in ops). |
| Accounting | 25 | **15** | Balanced/immutable/idempotent posting with DB CHECK, Decimal in new flows, overpayment-safe locking. Deduct: unposted entries in statements (P1), loss-breaks-balance-sheet (P1), float math (P1), settings-type asymmetry (P2). |
| Data integrity | 20 | **15** | Per-tenant uniques, PROTECT FKs, ledger tie-invariant, migrations clean. Deduct: tenant-less line tables (P2), tenant CASCADE delete (P2), no DB quantity/non-negative CHECKs (P3). |
| Test confidence | 15 | **10** | 274 green, superb cross-tenant matrix + inventory tie; genuine, broad unit/API coverage. Deduct: no concurrency/conssus tests, no net-loss report test, no status-enforcement tests, no UI tests (P1 bug slipped through). |
| Performance | 10 | **6** | Good indexes. Deduct: no pagination, N+1 paid/outstanding, no Celery tasks, tight 100/h throttle. |
| Documentation/ops | 5 | **3** | Spec-kit artifacts + report + health endpoint + compose are excellent. Deduct: no runbook, no observability (no structured logging/sentry), no email/queue integration, committed dev scripts. |
| **Total** | **100** | **63 / 100** | |

Scoring note: the 63 reflects "very strong foundation, several production-blocking gaps". The P1s are individually small fixes; none require redesign.

---

## 20. Recommended Next Steps (prioritized — not implemented)

**Phase 1 — correctness & integrity (must-do before go-live):**
1. [P1-1] Exclude unposted entries from ledger/reports; make the Journal UI actually post (or auto-post). Tests for draft-exclusion.
2. [P1-2] Fix balance-sheet clamping so net losses flow to equity; regression test that the balance sheet balances with a loss.
3. [P1-3] Frontend: persist rotated refresh + single-flight refresh; keep session across lifetime.
4. [P1-4] Frontend: `key`-remount/reset for the invoice modal (apply the shared pattern from the payment pages).
5. [P1-5] Convert accounting service + serializer money math to `Decimal`/quantized.
6. [P1-6] Implement an append-only audit-log service + model (intro as its own hardening feature with migrations + tests + admin).
7. [P1-7] Enforce `User.status == ACTIVE` and `Tenant.status == ACTIVE` in permission/auth paths (and on `/tenants/switch/`).

**Phase 2 — hardening (before public launch / scaling):**
8. [P2] Bind invitation acceptance to the invited email; email the token (introduce mailer + Celery task as the first §VII async task).
9. [P2] Row-lock the invoice during draft→posted transitions (parity with payments).
10. [P2] Add tenant_id columns to line tables (or document the deviation in the constitution with explicit approval per §Governance), and flip `Tenant` FK to `PROTECT` with a decommission workflow.
11. [P2] Move tokens out of `localStorage` (short-lived access + HttpOnly refresh cookie) and add a strict CSP.
12. [P2] Enforce a shared "tenant membership + active" permission base class to eliminate the middle-layer trust reliance.
13. [P2] Rebalance throttling (raise user rate; add dedicated login throttle/lockout).
14. [P2] Ensure post-time settings checks validate account type symmetrically across sales/purchases/inventory.

**Phase 3 — productization:**
15. [P3] Pagination + eliminate the paid/outstanding N+1; keep reports Decimal.
16. [P3] CI wiring for lint+build+full suite; add the missing test band (concurrency, net-loss, status enforcement, invitation binding, refresh rotation).
17. [P3] Remove/guard `debug_account.py`, `check_user.py`; add `.env.example`; document ops runbook + observability.

---

## 21. Final Recommendation

**B — fix the Phase-1 blockers before production go-live and before starting Feature 013.**

The core accounting/inventory posting engine is sound, well-tested, and tenant-isolated, and there are **no P0 issues**. But with seven P1s — including reports leaking unposted drafts, a balance sheet that breaks in loss periods, a guaranteed daily logout loop, a data-loss modal bug, float money math, no audit trail, and no enforcement of disabled/suspended states — this build is **READY WITH CONDITIONS**, not READY. All Phase-1 items are small, precisely scoped fixes suitable for a focused hardening pass; a full independent re-audit (C) is not required.

---

## Appendix A — Evidence rules & confidence

- **Classification labels** used per finding: `V` confirmed vulnerability (exploitable as-is), `B` confirmed bug (wrong behavior, no privilege boundary), `A` architectural risk (safe today only under stated assumptions), `T` missing test, `R` recommendation.
- **Confidence**: findings marked off direct file:line inspection are High; findings synthesized across the two subagent passes (frontend sweep, spec-kit compliance) are High for behavioral claims reproduced by reading the code paths above (AUD-003/004/009/017/018/027 verified line-by-line in this session; AUD-004/P1-1/P1-2/P1-7 re-verified directly).
- **Threat-model caveat (AUD-010/AUD-011/AUD-013)**: these are conditions under which issues *would* arise (future endpoint, future table, a second writer) rather than observed exploits; they are labeled A and must be read as hardening requirements, not as current breakage.
- **DB-level CHECK tolerance (AUD-030)** and the **float balance tolerance (AUD-005)** are reported as precision/robustness matters; neither can be triggered to profit from the UI today (services enforce Decimal-exact JEs before the CHECK is consulted).
- **Not reviewed**: third-party package versions (SBOM), infra secrets in CI/CD, TLS termination config, backup/DR, Sentry/APM, email provider, and the contents of `.env` files (confirmed untracked/ignored). These are out of scope for a source audit and are listed for completeness as ops follow-ups.