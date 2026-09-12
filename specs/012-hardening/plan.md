# Implementation Plan: 012-H Production Hardening

**Branch**: `012-inventory` · **Ref**: AUD-001 P1 findings · **Created**: 2026-09-12

## Objective

Eliminate all seven P1 production blockers from AUD-001 without touching Feature 013 scope, preserving the 292-test baseline and adding hardening regression tests. Implementation is sequential: each phase keeps the suite green before the next begins.

## Phases

### Phase H1 — P1-1 Manual Journal / Financial Reports (partially in HEAD `ec5563a`)

- Ledger aggregation filters `entry__posted=True` (`LedgerService.get_ledger`).
- Report aggregation filters `entry__posted=True` (`ReportService._line_aggregation`).
- Journal UI: `JournalEntryForm` submit acts as **Save Draft**; `JournalPage` exposes an explicit **Post** button per draft row calling `/journal-entries/{id}/post/`.
- `JournalEntrySerializer` exposes the `posted` flag so lists can render the Draft/Posted badge.

**Tests**: draft excluded from ledger / trial balance / income statement / balance sheet; posted entry included; explicit post moves a draft into reports; posting remains balanced; posted JE immutable (405 on update/delete).

### Phase H2 — P1-2 Balance Sheet Net Loss (in HEAD `ec5563a`)

- `build_section` no longer clamps with `max(bal, 0)`; signed balances carry through.
- `net_income = total_revenue - total_expense` is signed and added as a "Retained Earnings (Current Period)" equity line; no `max(..., 0)`.

**Tests**: loss period balances (`total_assets == total_liabilities_and_equity`), profit period balances, break-even balances, negative asset balance not hidden, tenant isolation.

### Phase H3 — P1-5 Decimal Accounting (in HEAD `ec5563a`)

- `JournalEntryService.post_entry`: `sum(..., Decimal("0"))` with **exact** `total_debit != total_credit` rejection (tolerance removed).
- `LedgerService` running balances/totals in `Decimal`, output quantized `:.4f`.
- `ReportService` aggregation in `Decimal`.
- `JournalEntrySerializer.validate` in `Decimal`, exact equality.

**Tests**: exact balanced JE; fractional Decimals (0.0001); multi-line aggregation; report totals; running ledger balances; imbalance-of-one-thousandth rejected at both serializer and service; values near rounding boundaries.

### Phase H4 — P1-3 Refresh Token Rotation (working tree)

- Backend already `ROTATE_REFRESH_TOKENS=True`; rotation tested.
- `frontend/src/services/api.js`: single-flight `refreshAccessToken()` (shared in-flight promise), persists `data.access` **and** `data.refresh`, replaces the old refresh token, retries the original request; `_retry` guard prevents loops; only a genuine refresh failure clears storage and redirects.

**Tests**: `TokenRotationTests` (returns new access + refresh; old refresh blacklisted; rotated refresh reusable exactly once; rotated access works). Frontend manual-verification documented (no UI harness).

### Phase H5 — P1-4 Invoice Modal Reset (working tree)

- `InvoicesPage.jsx` renders `<InvoiceForm key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')} .../>` so each open/create seeds fresh state (parity with payments/purchases pages).
- `InvoiceForm.jsx` first-mount `useState(seededForm(invoice))` now always receives a freshly mounted component.

**Verification**: manual create → edit A → close → edit B → save flow; A→B→A transitions; documented in `quickstart.md`.

### Phase H6 — P1-7 Disabled Users / Suspended Tenants (working tree)

- `apps/core/permissions.py`: `TenantScopedPermission` base — rejects unauthenticated requests, non-`ACTIVE` users, missing `tenant_id`, and memberships whose tenant is not `ACTIVE`; subclasses declare `allowed_roles`.
- All app permission classes inherit it (accounts/accounting/sales/purchases/inventory).
- `BlacklistCheckingJWTAuth.authenticate` rejects a disabled user's already-issued token with 401 and sets request audit context from the validated token.
- `tenant_switch_view` returns 403 when the target tenant is not `ACTIVE`.

**Tests**: `test_status_enforcement.py` — active access allowed; disabled user (valid token) rejected; disabled user cannot switch; disabled refresh rejected; suspended/cancelled tenant denied per-tenant and via switch; active switch OK.

### Phase H7 — P1-6 Immutable Audit Trail (working tree)

- `apps/core/models.py`: `AuditLog` (append-only; `save`/`delete`/`update` guarded; `objects.delete/update` raise `TypeError`); migration `0002_auditlog`.
- `apps/core/audit.py`: `AuditService.record` + request-context helpers (thread-local, set by middleware + auth), recursive `_sanitize` stripping sensitive keys, JSON normalization.
- `apps/core/middleware.py` + `accounts/auth.py`: set/clear the request audit context.
- Service-layer audit calls: accounts (register, invitation create/accept/cancel, member role change/remove), accounting (account create/update/deactivate, journal create/post), settings (sales/purchase/inventory), financial documents (sales/purchase invoice create/update/post/delete, payment create/update/post/delete, inventory adjustment create/update/post/delete).

**Tests**: `test_audit_trail.py` — record created with correct tenant/actor/action/target; before/after snapshots; immutable (no update/delete/bulk-update); cross-tenant isolation; failed operation writes nothing; sensitive keys scrubbed; secrets never persisted.

## Regression Gate (after every phase)

- `cd backend; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q` — all pass.
- `py manage.py makemigrations --check --dry-run` — "No changes detected".
- `frontend`: `npm run build` and `npm run lint` — zero new problems over the 16-problem baseline.

## Final Gate

Full backend suite ≥ 274 + hardening tests (target 324 passed, 1 postgres-only skip), migrations clean, frontend build green, lint still exactly 16 (all pre-existing). Commit hardening work as `fix: resolve production readiness blockers`. Do not push. Do not deploy. Feature 013 not created.