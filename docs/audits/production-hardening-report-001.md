# Production Hardening Report — Cetrak Accounting System

- **Report ID**: PROD-HARDENING-001
- **Date**: 2026-09-12
- **Agency**: opencode (resolving AUD-001 P1 findings), verified by full regression
- **Scope**: AUD-001 (`docs/audits/production-readiness-audit-001.md`) P1 findings P1-1 … P1-7
- **Constraint honored**: Feature 013 not created; no P2/P3 work; no push; no deploy

---

## 1. Baseline

| Artefact | AUD-001 baseline (commit `8d3902b`) | After hardening (working tree) |
|---|---|---|
| Backend suite | 274 passed, 1 skipped | **324 passed, 1 postgres-only skip** |
| Migrations drift | clean | `makemigrations --check --dry-run` → "No changes detected" |
| Frontend build | clean | clean (vite, 130 modules, 399.05 kB JS / 110.26 kB gzip) |
| Frontend lint | 16 problems (15 errors, 1 warning) | **16 problems — identical, all pre-existing, zero new** |
| Audit | none | append-only `core_audit_log` + `AuditService` (17 tests) |
| Status enforcement | not enforced on sessions | `TenantScopedPermission` + JWT-auth user check (10 tests) |
| Refresh rotation | refresh token dropped (frontend) | persisted + single-flight (4 rotation tests) |
| Invoice modal | state seeded once | `key`-remount per editing record |
| Reports | unposted drafts included; net-loss breaks BS | `posted=True` filters; signed balances; Decimal math |

Commit `ec5563a` (immediately post-baseline, kept in this pass) already delivered the backend half of P1-1/P1-2/P1-5 plus the Journal UI posting flow and 18 integrity tests; this hardening pass completed the remaining P1 scope (P1-3, P1-4, P1-6, P1-7) and verified all seven end-to-end.

---

## 2. Findings addressed

| ID | Finding | Resolution | Evidence |
|---|---|---|---|
| **P1-1** (AUD-001) | Unposted JEs flow into Ledger/TB/IS/BS; UI never posts | Ledger + all report aggregation filter `entry__posted=True`; UI: **Save Draft** creates, explicit **Post** (`/journal-entries/{id}/post/`) promotes; `posted` surfaced in list | `accounting/services.py:200,251`; `JournalPage.jsx`; `test_financial_integrity.py` |
| **P1-2** (AUD-002) | BS clamps losses → does not balance | `max(bal,0)` removed; signed net income/loss added to equity as "Retained Earnings (Current Period)" | `accounting/services.py:351-394`; net-loss test balances |
| **P1-3** (AUD-003) | Rotated refresh dropped → daily forced logout | Single-flight `refreshPromise`; persists `data.access` **and** `data.refresh`; retries original request; clears only on genuine failure | `frontend/src/services/api.js`; `TokenRotationTests` |
| **P1-4** (AUD-004) | Invoice modal overwrites record B with stale/blank data | `<InvoiceForm key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')} …/>` remounts per record | `InvoicesPage.jsx:163`; manual checklist |
| **P1-5** (AUD-005) | Float money in accounting services/serializer | All accounting math in `Decimal`; exact equality (tolerance removed); quantized `{:0.4f}` output; `_as_decimal` coercions | `accounting/services.py`, `serializers.py`; boundary tests |
| **P1-6** (AUD-006) | No audit trail | `AuditLog` (append-only) + `AuditService.record` from every service-layer mutation; request context via middleware + JWT auth; sanitization; immutability guards | `core/{models,audit,middleware}.py`, service layers, migration `core/0002`, `test_audit_trail.py` |
| **P1-7** (AUD-007) | Disabled users / suspended-cancelled tenants keep API access | Shared `TenantScopedPermission` (active user + ACTIVE tenant + membership role) replaces duplicated per-app logic; `BlacklistCheckingJWTAuth` rejects disabled users on valid tokens; switch refuses non-ACTIVE tenants | `core/permissions.py`, `accounts/auth.py`, `accounts/views.py`, `test_status_enforcement.py` |

---

## 3. Implementation summary

**Backend — accounting (computational, no migration):**
- `LedgerService.get_ledger` and `ReportService._line_aggregation` require `entry__posted=True`.
- `JournalEntryService.post_entry` validates with Decimal exact equality; ledger/report Math fully `Decimal`.
- `ReportService.balance_sheet` carries signed balances and a signed retained-earnings line.

**Backend — audit trail (new):**
- New `core.AuditLog` model + migration `0002_auditlog.py`; append-only via guarded `save`/`delete`/`update` and queryset `update`/`delete` raising `TypeError`.
- New `core/audit.py`: `AuditService.record(…)` (single service-layer entry point), thread-local request context (`set_request_context` / `clear_request_context`), recursive `_sanitize` stripping sensitive keys, JSON normalization of `Decimal`/`UUID`/`datetime`.
- Middleware clears context per request; `BlacklistCheckingJWTAuth.authenticate` populates actor/tenant/metadata from the validated token and rejects non-ACTIVE users.
- Audit calls added to: `accounts/services.py` (register, invitation create/accept/cancel, member role-change/remove), `accounting/services.py` (account create/update/deactivate, journal create/post), `sales/services.py`, `purchases/services.py`, `inventory/services.py` (settings updates, invoice/payment/adjustment create/update/post/delete).

**Backend — authorization:**
- New `core/permissions.py` `TenantScopedPermission` base; `allowed_roles` per class; one membership+tenant ACTIVE query.
- Refactored `accounts`, `accounting`, `sales`, `purchases`, `inventory` permission modules to inherit it (equivalent role sets, reduced duplication).
- `tenant_switch_view` returns 403 when the target tenant is not ACTIVE.

**Frontend:**
- `api.js`: single-flight refresh with rotated-refresh persistence and original-request retry; session cleared only on genuine failure.
- `InvoicesPage.jsx`: `InvoiceForm` remount `key` per editing identity (parity with payment/purchase pages).

---

## 4. Files changed

**New:**
- `backend/apps/core/audit.py` — `AuditService` + request-context helpers
- `backend/apps/core/permissions.py` — `TenantScopedPermission`
- `backend/apps/core/migrations/0002_auditlog.py` — `AuditLog`
- `backend/apps/core/tests/__init__.py`, `backend/apps/core/tests/test_audit_trail.py` (17 tests)
- `backend/apps/accounts/tests/test_status_enforcement.py` (10 tests)
- `specs/012-hardening/{spec,plan,tasks,report,quickstart,data-model}.md`, `specs/012-hardening/checklists/requirements.md`
- `docs/audits/production-hardening-report-001.md` (this report)

**Modified (backend):**
- `core/models.py` (AuditLog), `core/middleware.py` (context clear)
- `accounts/auth.py` (disabled-user rejection + audit context), `accounts/views.py` (switch guard), `accounts/services.py` (audit), `accounts/permissions.py`
- `accounting/services.py` (audit; report/posted + Decimal + BS already in HEAD `ec5563a`), `accounting/permissions.py`
- `sales/services.py`, `purchases/services.py`, `inventory/services.py` (audit calls), and their `permissions.py`
- `accounts/tests/test_auth_api.py` (`TokenRotationTests`, +4)

**Modified (frontend):**
- `services/api.js` (single-flight + rotate-refresh persistence)
- `pages/sales/InvoicesPage.jsx` (modal remount `key`)

**Documentation:**
- `AGENTS.md` (status), `specs/012-hardening/*`, `docs/audits/production-hardening-report-001.md`

---

## 5. Migrations

- One new migration: `apps/core/migrations/0002_auditlog.py` (adds `core_audit_log`).
- `py manage.py makemigrations --check --dry-run` → **"No changes detected"**.

---

## 6. Tests added

| Suite | # | Covers |
|---|---|---|
| `accounting/tests/test_financial_integrity.py` (HEAD `ec5563a`, retained) | 18 | draft excluded from ledger/TB/IS/BS; posted included; explicit post; immutable posted JE; net-loss/profit/break-even BS balance; negative balance not hidden; Decimal exactness; imbalance-of-0.001 rejected; tenant isolation |
| `accounts/tests/test_auth_api.py::TokenRotationTests` | 4 | new access+refresh returned; old refresh blacklisted; rotated refresh reusable exactly once; rotated access works |
| `accounts/tests/test_status_enforcement.py` | 10 | active allowed; disabled-with-valid-token rejected; disabled cannot switch; disabled refresh rejected; suspended/cancelled tenant rejected; switch refuses suspended/cancelled; active switch OK |
| `core/tests/test_audit_trail.py` | 17 | record creation w/ tenant/actor/action/target; before/after snapshots; immutability (no update/delete/bulk); cross-tenant isolation; no record on failed op; secrets scrubbed |
| **Total new vs 274 baseline** | **50** | **324 passed, 1 skipped** |

---

## 7. Full regression result

```
py -m pytest apps/ -q   (DJANGO_SETTINGS_MODULE=config.settings.test)
→ 324 passed, 1 skipped in 13.56s
```

All pre-existing tests preserved (274 baseline + 50 new). Tenant-isolation and 18-test financial-integrity suites green. Postgres-only row-lock skip unchanged.

## 8. Frontend build result

```
npm run build  →  vite build  ✓ built in 331ms
130 modules transformed • dist/assets/index-*.js 399.05 kB (gzip 110.26 kB)
```

## 9. Frontend lint result

```
npm run lint → ✖ 16 problems (15 errors, 1 warning)
```

Identical to baseline; the changed files (`api.js` clean; `InvoicesPage.jsx` carries 2 pre-existing `react-hooks/set-state-in-effect` errors on its data-fetch effects, untouched by the single added `key` attribute) introduce **zero new problems**.

---

## 10. Constitution compliance changes

| Section | Change |
|---|---|
| **§II Immutable audit trail** | **Satisfied.** Audited mutation set now complete for accounts, membership, settings, and financial documents via `AuditService`; audit rows are append-only and immutable at the application layer. |
| **§II No float money** | **Satisfied** for the accounting service/serializer layer (exact `Decimal` equality). |
| **§II No direct edits to posted entries** | Preserved; audit adds an additional immutable log on top. |
| **§I Tenancy** | Improved: `TenantScopedPermission` centralizes membership + ACTIVE-tenant checks; audit rows are tenant-flagged. Note: `AuditLog` uses `SET_NULL` for tenant/actor so history persists if a tenant is removed from membership (deletion itself remains CASCADE per pre-existing AUD-012/P2). |
| **§III / §IV** | Unchanged and compliant; all checks centralized in existing auth/permission layer (no view-layer business logic added). |
| Remaining deviations (unchanged, out of scope) | §VI bcrypt (AUD-025), §VII Celery/zero tasks (AUD-026), §I four tenant-less line tables (AUD-011) — documented in AUD-001 §18. |

---

## 11. Remaining P2/P3 items (not addressed — scope)

Unchanged from AUD-001, for future phases:
- **P2**: AUD-008 (invitation not email-bound / not emailed), AUD-009 (tokens in localStorage → HttpOnly), AUD-010 (JWT claim trust / middleware membership gate), AUD-011 (tenant-less line tables), AUD-012 (tenant CASCADE delete), AUD-013 (draft-post row lock), AUD-014 (throttling/lockout), AUD-016 (post-time settings type-check symmetry), AUD-017 (tenant-drift refresh during switch), AUD-025 (bcrypt), AUD-026 (Celery).
- **P3**: AUD-018 (frontend error rendering), AUD-019 (silent `except ValueError`), AUD-020 (dead `JournalEntryViewSet.create` route gap), AUD-021 (me_view writable status/email), AUD-022 (least-privilege guards), AUD-023 (dev scripts), AUD-027 (dead `.env` var), AUD-028 (public health), AUD-029 (pagination/N+1), AUD-030 (PG CHECK float tolerance).
- **AUD-024** gaps now partially closed (net-loss, status enforcement, refresh rotation, audit); concurrency and invitation-email-binding still untested.

---

## 12. Known limitations

1. Audit immutability is application-layer (guarded ORM + no write endpoints); no DB-level trigger/revoke. Documented in `specs/012-hardening/data-model.md`.
2. No UI test harness exists ⇒ P1-3 single-flight and P1-4 modal reset rely on manual verification (`specs/012-hardening/quickstart.md`), plus unit coverage for the backend rotation half.
3. Audit rows only accrue for operations performed after `core/0002` deploys; no backfill of history.
4. `Test` settings use `config.settings.test`; Postgres-specific row-lock path remains skipped in CI (unchanged).

---

## 13. Final readiness assessment

All **seven P1** items from AUD-001 are **resolved and verified**:

| Acceptance criterion | Status |
|---|---|
| Draft JEs excluded from all financial reports | ✅ (tests) |
| Journal UI has real posting behavior | ✅ (Save Draft + Post) |
| Balance Sheet balances in profit and loss | ✅ (tests) |
| Accounting money is Decimal; no new float | ✅ |
| Rotated refresh token persisted; single-flight; genuine-failure logout | ✅ (tests + manual) |
| Disabled users / suspended-cancelled tenants rejected | ✅ (tests) |
| Invoice modal resets reliably; no silent overwrite | ✅ (manual) |
| Audit log exists, tenant-scoped, immutable, secrets scrubbed | ✅ (tests) |
| Full backend suite ≥ 274 | ✅ 324 passed, 1 skipped |
| Frontend build passes; zero new lint problems | ✅ |
| Migrations clean | ✅ |
| Tenant isolation green | ✅ |

**Verdict: READY WITH CONDITIONS lifted to READY for the audited P1 scope.** The seven production blockers are closed with regression coverage; remaining P2/P3 items and broadened productization are documented for subsequent phases. Nothing pushed, nothing deployed, Feature 013 not created.