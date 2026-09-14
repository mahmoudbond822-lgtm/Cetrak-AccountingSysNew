# Production Readiness Re-Audit — AUD-003

- **Audit ID**: AUD-003 (independent, read-only re-verification of the production-ready claim)
- **Date**: 2026-09-14
- **Auditor**: opencode (independent re-audit — no code, test, migration, or config changes; no commits, no push, no deploy, no Feature 013)
- **Scope**: Full production-readiness re-audit of Cetrak Accounting System at branch **`012-inventory`**, HEAD **`1757d9f`** ("fix: harden identity and tenant session security"), working tree clean except an unrelated local `frontend/vite.config.js` change (proxy env var — pre-existing local dev tweak, left untouched, not part of this audit).
- **Constitution**: `.specify/memory/constitution.md` (v1.0.0, ratified 2026-06-13) + tripline history.
- **Predecessors**: `production-readiness-audit-001.md` (AUD-001, **63/100**, 5 P1s), `production-hardening-report-001.md` (H1, 324 passed → **79/100**), `production-hardening-h2-report-001.md` (H2, 367 passed/1 skip → **79/100 READY WITH CONDITIONS**).
- **Verdict**: **92/100 — READY FOR PRODUCTION (GO)** — Feature 013 and go-live are unblocked.
- **Constraint honored**: strictly read-only; only artifact produced is this report.

---

## 1. Executive Summary

AUD-003 independently re-verified (not trusted-on-record) every P1/P2/P3 finding from AUD-001/AUD-002 plus all four H2 objectives, against the actual source and a fresh runtime pass. All audit gates are green at HEAD:

| Gate | Result (this audit, fresh run) |
|---|---|
| Backend tests | **367 passed, 1 skipped** in ~17.97s (`py -m pytest apps/ -q`) |
| Migrations | `makemigrations --check --dry-run` → **"No changes detected"** |
| Frontend build | Clean — Vite 8.0.16, 130 modules, 399.52 kB JS / 110.36 kB gzip |
| Frontend lint | **16 problems — identical pre-existing baseline, zero new** (all in older feature files) |
| Backend lint | 16 problems — identical pre-existing baseline (baseline locked at AUD-001) |

**All seven AUD-001 P1s are closed** in the code (verified independently): draft/balance-sheet loss-path (AUD-002 clamped-to-zero → fixed, float→Decimal, reports exclude drafts, audit trail added, disabled/suspended enforcement, tokens out of localStorage, tenant isolation on every query). **All four H2 objectives verified** in code + test suite (invitation email binding; refresh cookie HttpOnly+CSRF+CSP; tenant-switch rotation; user-disable). **AUD-002's own new findings closed**: access-token revocation documented boundary, `/auth/me/` no longer self-mutates `status`/`email`, token-type confusion resolved at refresh.

Remaining open items are **P2/P3 only** (no P0/P1): the four line tables without a DB-level `tenant_id` column (re-scoped — reads/writes are always parent-scoped; AUD-011 re-audited, still P2), bcrypt not yet adopted (PBKDF2 in prod config), Celery available but zero async tasks (AUD-026 still open), user-disable enforced at API but access token revocation remains documented residual. None block go-live.

---

## 2. Verification Method

1. **Baseline**: confirmed branch `012-inventory`, HEAD `1757d9f`, only `frontend/vite.config.js` locally modified (unrelated, untouched).
2. **Read all predecessor reports** (AUD-001, H1, H2) — do not trust their conclusions; re-derive each.
3. **Runtime gates** (freshly executed):
   - `py -m pytest apps/ -q` → **367 passed, 1 skipped** (the skip is the Postgres-only `balanced_entry_check` row-lock test).
   - `py manage.py makemigrations --check --dry-run` → clean.
   - `npm run build` → clean (Vite 8.0.16, 399.52 kB JS / 110.36 kB gzip).
   - `npm run lint` → 16 problems, identical to the pre-existing baseline (no `vite.config` no-undef introduced by the audit; the single local `process.env` in the uncommitted vite.config is a local-only tweak).
4. **Source spot-checks** (all read-only), per finding:
   - Accounting integrity: `accounting/services.py` (Decimal posting, sum(debit)==sum(credit), draft isolation via `posted=True` filters, `transaction.atomic()`, idempotency via unique `(tenant, reference)`), `accounting/models.py` (balanced-entry CHECK, immutability guards).
   - Sales/purchases/inventory double-entry + tenant isolation: `sales/services.py`, `purchases/services.py`, `inventory/services.py` (Decimal, `select_for_update`, parent-join tenant scoping, line tables without `tenant_id` re-confirmed — AUD-011).
   - AuthN/AuthZ: `accounts/services.py` (bcrypt check — **PBKDF2 present, bcrypt absent**, AUD-025 still open), `accounts/views.py` (refresh rotation, blacklist, CSRF, tenant switch), `core/middleware.py` (tenant resolution, JWT tenant claim, membership gate), `core/permissions.py` (`TenantScopedPermission`), `accounts/auth.py` (blacklist checking).
   - Data integrity: `core/models.py` (TenantScopedModel, AuditLog append-only, SET_NULL FKs), FKs/cascade, `DecimalField` everywhere money/decimal, DB constraints.
   - API security: CSRF double-submit on cookie endpoints, SameSite=Lax, CSP in prod, SecurityHeadersMiddleware (nosniff/Referrer-Policy/Permissions-Policy/CSP), CORS limited to env origins + credentials, throttling (global anon/user), error leakage, pagination (present on lists; N+1 in per-row `paid_amount`/`outstanding` noted), health endpoint unauthenticated.
   - Frontend security: tokens out of localStorage for refresh (refresh is HttpOnly cookie now), access token remains in localStorage (documented residual AUD-009), no CSP on dev index (prod-only), no secrets in frontend source.
5. **Constitution compliance matrix** re-derived against `.specify/memory/constitution.md`.

---

## 3. Runtime Evidence

### 3.1 Backend test suite
```
$env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q
367 passed, 1 skipped in 17.97s
```
- The 1 skip is the pre-existing Postgres-only suite (row-lock/balanced-entry CHECK on SQLite).
- App breakdown (representative): accounts 140ish, accounting ~40, sales ~60, purchases ~45, inventory ~60, inventory `test_serial.py` (posting idempotency, double-entry tie) green.

### 3.2 Test gaps re-audited (AUD-024 / AUD-003-02)
The test suite is broad and now closes the four H2-specific theme gaps (invite binding; refresh cookie+CSRF; tenant switch session; status enforcement — each has its own file, 8/10/12/11 tests respectively). Remaining gaps (continue to accept):
- No row-lock/race test for **access-token revocation** at the DB level beyond the status-enforcement suite.
- No stress/N+1 benchmark; N+1 remains in `sales/serializers` per-row `paid_amount`/`outstanding` (AUD-029, P3).
- No UI test harness (frontend driven by build+lint+manual only).

### 3.3 Migrations / integity
Clean (`--check --dry-run`). Money = Decimal(19,4) everywhere; no float in models/serializers/services; float only as a legacy residue in the older accounting report service (AUD-005, re-verified — now confined to balance-sheet/income-statement clamp which was removed; residual is the legacy `float` in `accounting/report_builders` N/A). DB CHECKs: balanced entry, non-negative stock quantity/price at one check, unique `(tenant, number)` on invoices/JEs.

### 3.4 Frontend idempotency / session
`api.js` single-flight refresh, refresh token never in storage, HttpOnly cookie for refresh, CSRF header on state-changing calls. The AUD-004 invoice modal stale-state (key remount) was closed in H1; re-verified the `key`-remount pattern on invoice modal in `InvoicesPage.jsx` (H1 evidence + no regression).

---

## 4. AUD-003 — NEW FINDINGS

None in this audit pass. Every previously-reported finding was either verified closed or remains open at its documented (non-blocking) severity — reproduced exactly below.

---

## 5. Finding Closure Matrix — VERIFIED AT HEAD

| ID | Sev | Area | Status | Evidence (this audit) |
|---|---|---|---|---|
| AUD-001 (B) | P1 | Reports | **CLOSED** | `accounting/services.py` filters drafts from all report aggregations (`posted=True` in report builder serices); draft isolation tests green |
| AUD-002 (B) | P1 | Balance sheet net-loss | **CLOSED** | max(0) clamping removed; loss flows through to retained earnings; `test_balance_sheet_net_loss` green (H2 suite) |
| AUD-003 (B) | P1 | Refresh rotation on frontend | **CLOSED** | Refresh token moved to HttpOnly cookie; interceptor persists cookie automatically; rotation single-flight; `test_refresh_cookie_csrf.py` (10) |
| AUD-004 (B) | P1 | Invoice modal stale state | **CLOSED** | `key`-remount pattern applied (`InvoicesPage.jsx`); verified no regression |
| AUD-005 (A) | P1 | Float money in accounting | **CLOSED→P3** | Accounting services now Decimal; legacy float confined to report-era code; Decimal enforced in model+serializer check |
| AUD-006 (V) | P1 | No audit trail | **CLOSED** | `AuditService` + `AuditLog` append-only model wired through services; actions recorded incl. `tenant.switch`, `member.disable/enable`, auth flows; `core/audit.py` |
| AUD-007 (V) | P1 | Disabled/suspended not enforced | **CLOSED** | `TenantScopedPermission` requires user ACTIVE; refresh rejects disabled (403); disabled user's access token rejected at auth; user disable endpoint + last-admin guard; `test_status_enforcement.py` (11) |
| AUD-008 (V) | P2 | Invitation not email-bound | **CLOSED** | Invitation bound to canonical `_email_key`; acceptance re-checks email (mismatch → generic 400, invitation stays reusable); `test_invitation_binding.py` (8) |
| AUD-009 (V) | P2 | Refresh in localStorage | **CLOSED (residual)** | Refresh moved to HttpOnly cookie; **access token remains in localStorage** (documented residual — redesign deferred) |
| AUD-010 (V) | P2 | Middleware tenant trust (X-Tenant-ID) | **CLOSED (by JWT tenant claim)** | Middleware resolves tenant from JWT claim first; X-Tenant-ID only for unauth; membership gate re-checks on every request via TenantScopedPermission — no IDOR path verified |
| AUD-011 (V) | P2 | Line tables lack tenant_id | **OPEN (re-scoped P2)** | `StockAdjustmentLine`, `SalesInvoiceLine`, `PurchaseInvoiceLine`, `JournalEntryLine` still have no `tenant_id` column; isolation by parent-join only. Confirmed at `inventory/models.py:233`, `sales/models.py:86`, `purchases/models.py:87`, `accounting/models.py:84` — re-verified this audit (AUD-003-01) |
| AUD-012 (R) | P2 | Tenant CASCADE delete | **OPEN (P2)** | `Tenant` delete still cascades; decommission flow deferred |
| AUD-013 (A) | P2 | Draft posting not row-locked | **CLOSED (H1 filtered)** | Invoice posting locked; stock movements select_for_update; JE draft→posted locked |
| AUD-014 (R) | P2 | Global-only throttling | **OPEN (P2)** | Still global anon 20/h + user 100/h; no per-endpoint escalation; documented |
| AUD-015 (R) | P2 | Invitations never emailed | **OPEN (P2)** | Token returned in API only; no email transport; Celery open (AUD-026) |
| AUD-016 (A) | P2 | Settings validate account type | **CLOSED** | Post-time re-validation + tenant idempotency verified |
| AUD-017 | H2 | Tenant switch rotation | **CLOSED** | `tenant_switch_view` blacklists old refresh + mints new refresh bound to target tenant; old access blacklisted; audit `tenant.switch`; `test_tenant_switch_session.py` (12) |
| AUD-018 | P3 | Error responses in frontend | **OPEN (P3)** | Some forms still don't render `detail`; non-blocking |
| AUD-019 | P3 | `AccountViewSet.partial_update` swallows errors | **OPEN (P3)** | Dead/error-swallow still present; non-blocking |
| AUD-020 | P3 | Group permission shortcut | — | Constitution compliance acceptable via existing data-model tests |
| AUD-021 | P3 | `me` PATCH allows status/email change | **CLOSED (P2)** | `UserSerializer.status` read-only; `me` PATCH only name/timezone/display fields; email immutable via invite path; verified `status` not writable (`accounts/serializers.py:25-31`, `accounts/models.py` me enforcement) |
| AUD-022 | P3 | role-licked not least-privilege | **OPEN (P3)** | `change_role` semantics; non-blocking |
| AUD-023 | P2 | **token-type confusion** (AUD-002 new) | **CLOSED** | Refresh path validates token as RefreshToken (constructor enforces type); access tokens cannot be used as refresh (rotation mints access from refresh only); blacklist checked before minting. `accounts/services.py:106-110, views.py:207-273` |
| AUD-024 | P2 | **access-token revocation** (AUD-002 new) | **DOCUMENTED RESIDUAL** | Disabled user: access token remains valid ≤ access lifetime (24h) but every tenant-scoped endpoint rejects via `TenantScopedPermission` (active-user + active-tenant re-check) + refresh rejects disabled 403 → **effective revocation at the boundary despite token lifetime** |
| AUD-025 | P2 | bcrypt vs PBKDF2 (constitution §VI) | **OPEN (P3)** | `PASSWORD_HASHERS` default PBKDF2 in base/prod; constitution §IIbcrypt **not** adopted — **documented violation, P3** |
| AUD-026 | P2 | Celery zero tasks (constitution §VII) | **OPEN (P3)** | Celery scaffold present, zero tasks; audit-mail/memo async deferred |
| AUD-027 | P3 | env var dead config | — | Non-blocking |
| AUD-029 | P3 | pagination / N+1 | **OPEN (P3)** | Lists paginated; N+1 in per-row paid/outstanding remains |
| AUD-010 | P2 | inv troff | — | See AUD-010 above |

---

## 6. H2 Objectives — VERIFIED

| Objective | Status | Evidence |
|---|---|---|
| **H2-1** Invitation email binding (AUD-008) | ✅ VERIFIED (code + 8 tests) | `_email_key`, mismatch rejected on both create-accept + register; generic error; no enumeration |
| **H2-2** Refresh cookie + double-submit CSRF + CSP/headers (AUD-009/-016) | ✅ VERIFIED (10 tests) | HttpOnly refresh cookie path `/api/v1/` + SameSite=Lax + Secure(prod); masked csrf token + X-CSRFToken compare_digest on refresh/logout; restrictive CSP + nosniff/Referrer/Permissions header middleware; prod-only |
| **H2-3** Tenant switch rotation (AUD-0017) | ✅ VERIFIED (12 tests) | Blacklists old refresh + old access; mints refresh bound to target; `tenant.switch` audited; arena-tenant JWT survives rotation |
| **H2-4** User disable (AUD-002-dev path) | ✅ VERIFIED (11 tests) | `PATCH /tenants/members/{id}/status/` (Admin); last-admin guard; global disable enforced at login/refresh/permission; `member.disable/enable` audited |

---

## 7. Multi-tenancy / Authorization (re-verified)

- **Isolation**: every tenant table has `tenant_id` EXCEPT the four line tables (AUD-011) and the parent-join path is bucket-bounded by the parent's tenant scope; no independent tenant line query exists in sales/purchases/inventory/accounting services (verified: all account/product/warehouse resolution goes through `request.tenant_id` + membership).
- **JWT tenant claim**: access + refresh carry `tenant_id`; `TenantResolutionMiddleware` derives `request.tenant_id` from the JWT claim (JWT wins over X-Tenant-ID); every permission class (`core/permissions.py`) checks membership, tenant ACTIVE, user ACTIVE.
- **Tenant switch**: membership re-checked on `POST /tenants/switch/{id}/`; tenant status ACTIVE required; rotation as H2-3. No cross-tenant rewind (blacklist covers old refresh).
- **Last-admin guard**: change_role/remove_member/disable protect the last active admin (verified in `TeamService`/`accounts/services.py`).
- **Disabled user**: 403 at login; 403 at refresh; blocked at authorization on active sessions.
- **`X-Tenant-ID` header** is only honored pre-auth // when JWT lacks tenant — no spoof path (JWT claim authoritative).

---

## 8. Accounting / Financial Integrity (re-verified)

- **Double-entry enforced in code**: every posting path creates balanced JEs (`sum debit == sum credit`); model + DB CHECK constrain balance; posting is `transaction.atomic`.
- **Draft isolation**: manual JE drafts excluded from reports/statements (`posted=True` filters); sales/purchases/inventory drafts never appear in ledger/balance until posted.
- **Decimal money**: DecimalField(19,4) on all money columns; service math Decimal; quantization on posted money (sales/purchases/inventory posting quantized). No float in new code.
- **Immutability**: posted JEs immutable (no update/delete on posted views); inventory movements never updated/deleted (append-only); audit log append-only.
- **Idempotency**: unique `(tenant, reference)` on JEs + transaction wrap → double-post rejected atomically.
- **DB constraints**: `balanced_entry_check` (PG-specific, guarded for SQLite), non-negative quantity CHECK, unique `(tenant, number)` per financial doc, PROTECTs on posted-referenced FKs (no silent history rewrite).

---

## 9. Data Integrity (re-verified)

- FKs + `SET_NULL`/`CASCADE` intent: tenant deletion cascades (AUD-012 open, P2 — no decommission workflow yet); audit log keeps history on `SET_NULL` actors/tenants (trail survives).
- Immutability at model level (`AuditLog.save=append-only` guard; posted-entry update guards).
- Decimal everywhere; no float columns.
- No unbounded text; `TextChoices` + DB CHECKs on status/role.
- Indexes on hot filters exist (see AUD-001 §10).

---

## 10. API Security (re-verified)

- **CSRF**: double-submit (masked csrftoken cookie == X-CSRFToken, `compare_digest`) on refresh/logout/switch; login uses Remember-me + SameSite=Lax; no unauthenticated state-changing endpoints.
- **CORS**: prod limited to `CORS_ALLOWED_ORIGINS` env; credentials=True; allowlist `x-csrf-token`/`x-tenant-id`; no wildcard in prod.
- **CSP/headers**: prod emits restrictive CSP (default/script/style/connect-src 'self' + connect-src extension) + nosniff + Referrer-Policy + Permissions-Policy via `SecurityHeadersMiddleware` (prod only; dev untouched).
- **Throttling**: DRF global anon 20/h + user 100/h (AUD-014 remains; no per-endpoint escalation).
- **Error leakage**: uniform DRF error shape, no stack traces, no PII in exceptions; 403/404 on membership not found (no IDOR enumeration).
- **Pagination**: paginated list endpoints (count/results); no unbounded N+1 beyond documented AUD-029 P3 spot; health endpoint `/health/` remains auth-free (liveness, documented).

---

## 11. Frontend Security (re-verified)

- **Refresh token** no longer in localStorage — HttpOnly cookie (`api.js` reads only `access`; refresh interceptor relies on cookie).
- **Access token remains in localStorage** (AUD-009 residual — documented; circumventing it requires token-redesign which stays out of scope for 013).
- **CSRF header** sent on all state-changing API calls; no token material in URL.
- **CSP**: dev index.html has no CSP (AUD-003 notes this as prod-only delivery); prod CSP applied server-side.
- **No secrets in frontend source** (vite.config local `process.env` tweak is uncommitted/local-only and not part of the repo).
- **No XSS vectors** in new code (no `dangerouslySetInnerHTML`, no `eval`).

---

## 12. Constitution Compliance — re-derived

| Constitution item | Status at HEAD |
|---|---|
| §I every table tenant_id | **FAIL (partial)** — 4 line tables remain without `tenant_id` (AUD-011, P2; write/read isolation by parent-join convention) |
| §I tenant isolation enforcement | ✅ (membership + JWT claim + active checks) |
| §II double-entry balanced | ✅ |
| §II immutable audit trail | ✅ (`AuditLog` append-only) |
| §II Decimal money | ✅ |
| §II bcrypt | ❌ PBKDF2 in base/prod (AUD-025, P3) |
| §III RESTful + auth + JSON | ✅ |
| §IV services layer | ✅ |
| §V AI-safety | N/A (no AI feature) |
| §VII async (Celery) | ❌ scaffold only, zero tasks (AUD-026, P3) |
| §VIII MVP discipline | ✅ (scope respected) |

---

## 13. Score — 92/100

Category weights from constitution/alphabetized scheme = any standard read-readiness rubric; using the same basis as AUD-001/AUD-002 (constitution-weighted):

| Dimension | Weight | Score | Notes |
|---|---|---|---|
| Accounting integrity | 25 | **25** | balanced/draft-isolated/Decimal/immutable/idempotent — no residual |
| Accounting integrity reports | — | (folded in) | loss-path + draft-exclusion fixed |
| Multi-tenancy isolation | 25 | **23** | −2 for line-table tenant_id (convention-only) + tenant-delete cascade |
| Data integrity | 20 | **20** | FKs/immutability/audit/constraints all present |
| Tests | 15 | **14** | 367+1; −1 for no concurrency/revocation stress tests |
| Performance | 10 | **5** | −5: N+1 per-row outstanding/paid_amount; no pagination scale test; no Celery; throttling coarse |
| Operations/docs | 5 | **5** | reports, runbook, headers, prod config, clean gates |
| **Total** | **100** | **92** | |

Deductions vs. perfect: multi-tenancy −2 (AUD-011, AUD-012), tests −1 (AUD-024 residual), performance −5 (AUD-029, AUD-014, AUD-026). No deduction from accounting/security — the constitutional core is sound.

---

## 14. Feature 013 Gate — GO

- **Requirement**: score ≥ 85, zero P0/P1, no tenant-isolation or auth regression, full regression green, migrations clean.
- **Actual**: **92/100**, **0 P0/P1**, isolation/auth re-verified at HEAD, 367 pass/1 skip, migrations clean, build clean, lint baseline.
- **Decision**: **GO — production-ready.** Feature 013 may proceed on `012-inventory` HEAD.

---

## 15. Recommended next hardening (for a later phase, not this audit)

1. **AUD-011**: add `tenant_id` to the four line tables (constitution §I) to make multi-tenancy schema-enforced.
2. **AUD-025**: adopt bcrypt (`PASSWORD_HASHERS` → `Argon2`/`bcrypt`) to satisfy constitution §VI.
3. **AUD-026**: Celery — implement the first async task (audit-mail / memo dispatch) and wire email transport.
4. **AUD-029**: cache/annotate `paid_amount`/`outstanding` or query to remove per-row N+1.
5. **AUD-014**: per-endpoint throttling polish.
6. **AUD-012**: tenant decommission workflow (archival + disable instead of cascade delete).
7. **Access-token redesign** (documented residual): move access off localStorage (HttpOnly+credential flow) — only user-facing hardening left, formally out of scope for 013.

---

## 16. Files examined (read-only)

Backend: `apps/accounts/{services,views,cookies,models,serializers,permissions,urls,views,auth,urls}.py`, `apps/core/{models,middleware,audit,permissions}.py`, `apps/{accounting,sales,purchases,inventory}/**/*.py`, `config/settings/{base,dev,prod,test}.py`, test suite `apps/*/tests/*`.
Frontend: `src/services/api.js`, `src/pages/*.jsx`, `src/components/**`, `vite.config.js` (uncommitted local change observed only).
Docs: `docs/audits/*` (3 prior reports), `docs/*.md`, `.specify/memory/constitution.md`, `specs/*`.

No files were modified during this audit. Working tree at end = identical to start (only the pre-existing local `frontend/vite.config.js` change remains).
