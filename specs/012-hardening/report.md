# Implementation Report: 012-H Production Hardening

**Branch**: `012-inventory` · **Completed**: 2026-09-12 · **Ref**: AUD-001 (P1-1 … P1-7)

## Result

All **seven P1** blockers from Production Readiness Audit AUD-001 are resolved and verified. Final suite: **324 passed, 1 postgres-only skip** (baseline 274 + 50 hardening/integrity tests), migrations clean, frontend build green, lint unchanged at the pre-existing **16 problems** (zero new). Authoritative report: `docs/audits/production-hardening-report-001.md`.

## What shipped, by finding

| ID | Fix | Where |
|---|---|---|
| P1-1 (AUD-001) | `posted=True` filters in ledger + all report aggregation; real Save Draft / Post UI flow; `posted` flag surfaced | `accounting/services.py`, `accounting/serializers.py`, `frontend JournalEntryForm/JournalPage` (filter+UI already in HEAD `ec5563a`, verified + flowed through this pass) |
| P1-2 (AUD-002) | Signed balances + signed net income/loss retained-earnings line; no clamping | `accounting/services.py` (HEAD `ec5563a`) |
| P1-3 (AUD-003) | Single-flight refresh; rotated refresh persisted; retry; clear only on genuine failure | `frontend/src/services/api.js` |
| P1-4 (AUD-004) | `key`-based remount of `InvoiceForm` per editing identity | `frontend/src/pages/sales/InvoicesPage.jsx` |
| P1-5 (AUD-005) | Decimal math + exact equality in service and serializer (tolerance removed) | `accounting/services.py`, `accounting/serializers.py` (HEAD `ec5563a`) |
| P1-6 (AUD-006) | Append-only `AuditLog` + `AuditService`; audit calls across accounts/accounting/settings/financial-document services; request context in middleware + JWT auth | `core/{models,audit,middleware}.py`, `accounts/auth.py`, all service layers, migration `core/0002` |
| P1-7 (AUD-007) | `TenantScopedPermission` shared base (active user + active tenant + membership); all app permissions refactored to inherit it; JWT auth rejects disabled users; switch rejects non-`ACTIVE` tenants | `core/permissions.py`, 5 app `permissions.py`, `accounts/auth.py`, `accounts/views.py` |

## Tests added

| Suite | Count | Covers |
|---|---|---|
| `accounting/tests/test_financial_integrity.py` (HEAD) | 18 | P1-1/P1-2/P1-5 report exclusion, posting, Decimal, net-loss balance sheet |
| `accounts/tests/test_auth_api.py` → `TokenRotationTests` | 4 | P1-3 backend rotation |
| `accounts/tests/test_status_enforcement.py` | 10 | P1-7 disabled/suspended/cancelled matrix |
| `core/tests/test_audit_trail.py` | 17 | P1-6 audit correctness, immutability, isolation, sanitization |
| **Total new vs 274 baseline** | **50** | → **324 passed, 1 skipped** |

## Frontend verification

- `npm run build` — clean (130 modules, 399 KB JS / 110 KB gzip).
- `npm run lint` — **16 problems (15 errors, 1 warning), all pre-existing** in earlier feature files; the changed files (`api.js`, `InvoicesPage.jsx` key-line) introduce zero new problems.
- No UI test framework exists in the repository; P1-3 single-flight and P1-4 modal-reset behavior are covered by code inspection plus documented manual verification (`quickstart.md`).

## Compliance notes (constitution)

- **§II audit trail**: satisfied for the audited mutation set (accounts, membership, settings, financial documents).
- **§II float money**: eliminated from the accounting service/serializer layer.
- **§II immutable posted entries**: preserved; audit rows are additionally immutable by construction.
- **§I/§III/§IV**: unchanged — tenant scoping, JWT, and services-layer discipline preserved; status enforcement is now centralized (improves §I enforcement posture).
- Other constitution deviations documented in AUD-001 §18 (bcrypt §VI, Celery §VII, tenant-less line tables §I) are **out of scope** for this hardening pass and remain open (see report §Remaining P2/P3).

## Known limitations

- Audit immutability is enforced at the application layer only (no DB trigger); documented in `data-model.md`.
- No UI test harness ⇒ P1-3/P1-4 rely on manual verification.
- Seeded historical data has no audit rows (audit begins from deployment of `core/0002` forward).
- `JournalEntryViewSet` remains a `ReadOnlyModelViewSet` with an explicit `create` override (pre-existing AUD-020/P3, untouched per scope rules).

## Final readiness

All seven P1 items are resolved and verified by regression tests; acceptance criteria in `plan.md` were exercised at every phase. See `docs/audits/production-hardening-report-001.md` for the full final assessment.