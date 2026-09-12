# Implementation Tasks: 012-H Production Hardening

Status per task: `[x]` complete (implementation close-out).

## Phase H1 — P1-1 Manual Journal / Financial Reports

- [x] Ledger aggregation filters `entry__posted=True` (`LedgerService.get_ledger`).
- [x] Report aggregation filters `entry__posted=True` (`ReportService._line_aggregation`: trial balance, income statement, balance sheet).
- [x] `JournalEntrySerializer` exposes `posted` flag in list output.
- [x] `JournalEntryForm` submit action relabeled **Save Draft** (draft creation only).
- [x] `JournalPage` renders a Draft/Posted badge and an explicit **Post** button per draft calling `postJournalEntry`.
- [x] Regression tests: draft excluded from ledger / trial balance / income statement / balance sheet.
- [x] Regression tests: posted entry included in all reports; explicit post promotes a draft into reports.
- [x] Regression tests: posting remains balanced; posted JE immutable (405 on update/delete).

## Phase H2 — P1-2 Balance Sheet Net Loss

- [x] `build_section` carries signed balances (no `max(bal, 0)`).
- [x] `net_income = total_revenue - total_expense` signed; added as "Retained Earnings (Current Period)" equity line (no `max(..., 0)`).
- [x] Regression tests: net-loss balance sheet balances; net-profit balance sheet balances; zero net income balances; negative asset balance not hidden; loss balance sheet tenant-isolated.

## Phase H3 — P1-5 Decimal Accounting

- [x] `JournalEntryService.post_entry` Decimal sums + exact equality (no 0.001 tolerance).
- [x] `LedgerService` running balances / totals in `Decimal`, quantized `:.4f` output.
- [x] `ReportService` aggregation in `Decimal`.
- [x] `JournalEntrySerializer.validate` Decimal + exact equality.
- [x] Regression tests: exact fractional 0.0001 balance; imbalance-of-one-thousandth rejected (serializer + service); exact ledger running balances; exact trial-balance totals; values near rounding boundaries.

## Phase H4 — P1-3 Refresh Token Rotation

- [x] Backend rotation verified (`ROTATE_REFRESH_TOKENS=True`; new access + refresh minted; old refresh blacklisted).
- [x] `frontend/src/services/api.js`: single-flight refresh promise; persists `data.access` + `data.refresh`; replaces old refresh token; retries original request; `_retry` loop guard; clear-session only on genuine refresh failure.
- [x] `TokenRotationTests`: returns new access + new refresh; old refresh blacklisted after rotation; rotated refresh reusable exactly once; rotated access issues a working token.
- [x] Frontend manual-verification flow documented (no UI test harness).

## Phase H5 — P1-4 Invoice Modal Reset

- [x] `InvoicesPage.jsx` renders `InvoiceForm` with `key={showModal ? (editing?.id ?? 'new-open') : (editing?.id ?? 'new-closed')}`.
- [x] Manual verification: create → edit A → close → edit B → save B → A→B→A round trip.

## Phase H6 — P1-7 Disabled Users / Suspended Tenants

- [x] `apps/core/permissions.py`: `TenantScopedPermission` base (active user + active tenant + membership role).
- [x] Refactored app permission classes to inherit the base: accounts, accounting, sales, purchases, inventory.
- [x] `BlacklistCheckingJWTAuth.authenticate` rejects non-`ACTIVE` users on already-issued tokens (401); sets request audit context.
- [x] `tenant_switch_view` returns 403 for non-`ACTIVE` tenants.
- [x] Tests: active allowed; disabled (valid token) rejected; disabled cannot switch; disabled refresh rejected; suspended/cancelled tenant rejected; suspended/cancelled switch rejected; active switch OK.

## Phase H7 — P1-6 Immutable Audit Trail

- [x] `AuditLog` model (append-only; guarded `save`/`delete`/`update`; SET_NULL actor/tenant FKs).
- [x] Migration `core/0002_auditlog.py`.
- [x] `apps/core/audit.py`: `AuditService.record`, request-context (thread-local), recursive sensitive-key scrub, JSON normalization.
- [x] Middleware + JWT auth set/clear request audit context.
- [x] Accounts audit: `auth.register`, `invitation.create`/`accept`/`cancel`, `member.role_change`, `member.remove`.
- [x] Accounting audit: `account.create`/`update`/`deactivate`, `journal.create`/`post`.
- [x] Settings audit: `settings.sales.update`, `settings.purchase.update`, `settings.inventory.update`.
- [x] Financial documents audit: sales/purchase invoice create/update/post/delete; payment create/update/post/delete; inventory adjustment create/update/post/delete.
- [x] Tests: correct tenant/actor/action/target; before/after snapshots; immutability (update/delete/bulk-update); cross-tenant isolation; no audit record on failed operation; sensitive secrets never persisted.

## Close-out

- [x] Full backend suite green (324 passed, 1 postgres-only skip).
- [x] `makemigrations --check --dry-run` → "No changes detected".
- [x] `npm run build` clean; `npm run lint` still exactly 16 pre-existing problems (zero new).
- [x] `specs/012-hardening/*` artifacts written.
- [x] `docs/audits/production-hardening-report-001.md` written.
- [x] AGENTS.md status updated.
- [x] Working-tree diff inspected; only hardening-scoped changes staged; committed as `fix: resolve production readiness blockers`. No push, no deploy, no Feature 013.