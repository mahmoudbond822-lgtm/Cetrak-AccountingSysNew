# Feature Specification: 012-H Production Hardening

**Feature Branch**: `012-inventory` (hardening phase)

**Created**: 2026-09-12

**Status**: Implemented (awaiting review)

**Input**: Production Readiness Audit **AUD-001** (`docs/audits/production-readiness-audit-001.md`) — verdict "READY WITH CONDITIONS", score 63/100, P0 = 0, P1 = 7, P2 = 12, P3 = 11. This feature eliminates the **seven P1 blockers** that block go-live. It is **not** Feature 013 and creates no new product feature scope.

## Scope

| Audit finding | P1 | Area | Resolution |
|---|---|---|---|
| AUD-001 | P1-1 | Manual journal / financial reports | Draft (unposted) JEs excluded from ledger, trial balance, income statement, balance sheet; Journal UI gains a real Draft → Post flow. Backend-report half delivered in commit `ec5563a`; UI posting confirmed in this hardening pass. |
| AUD-002 | P1-2 | Balance sheet net loss | Remove `max(bal, 0)`/`max(net_income, 0)` clamping; net loss flows signed into equity. Delivered in commit `ec5563a`. |
| AUD-003 | P1-3 | Refresh token rotation | Frontend persists the rotated refresh token, retries the original request, and runs single-flight refresh; only a genuine refresh failure clears the session. |
| AUD-004 | P1-4 | Invoice modal state reset | `InvoiceForm` remounts per record via `key={editing?.id ?? ...}`; create/edit/create and A→B→A transitions reload clean state. |
| AUD-005 | P1-5 | Float money math | Accounting service + serializer monetary math converted to `Decimal` with exact equality; quantized output consistent with `DecimalField(19,4)`. Delivered in commit `ec5563a`. |
| AUD-006 | P1-6 | Immutable audit trail | Append-only `core.AuditLog` model + `AuditService` helper called from every service layer mutation; immutable to update/delete; tenant- and actor-aware; secrets scrubbed. |
| AUD-007 | P1-7 | Disabled users / suspended tenants | `User.status == ACTIVE` enforced in `BlacklistCheckingJWTAuth`; `Tenant.status == ACTIVE` enforced in a shared `TenantScopedPermission` base used by every app permission class and on `/tenants/switch/`. |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Draft journal entries never move the books (P1-1)

An accountant drafts a manual journal entry from the Journal screen. The entry is created as a `Draft` and appears with a "Draft" badge; it must **not** appear in the Ledger, Trial Balance, Income Statement, or Balance Sheet. The accountant then explicitly **Posts** the entry; only then does it flow into all reports.

**Independent Test**: Full API test — create a balanced draft, assert empty ledger/report rows; post; assert the entry now appears everywhere; assert a re-POST fails; assert PUT/PATCH/DELETE on the journal returns 405.

### User Story 2 - The Balance Sheet balances in a loss period (P1-2)

A company books `Assets ≠ 0` and `Revenue < Expense` in a period. The Balance Sheet must show the net loss as a negative retained-earnings line and satisfy `total_assets == total_liabilities_and_equity`. It must still balance in a profitable or break-even period.

**Independent Test**: API tests posting a loss and a profit case with `Decimal` assertions on the three totals.

### User Story 3 - Sessions survive token rotation (P1-3)

With `ROTATE_REFRESH_TOKENS=True` the backend returns a fresh access **and** refresh token on every refresh. The frontend interceptor must save both, replace the old refresh token, retry the failed request, and share a single in-flight refresh across concurrent 401s. Only a real refresh failure clears storage and redirects to `/login`.

**Independent Test**: Backend rotation tests (new access + refresh returned; old token blacklisted; rotated token reusable exactly once); frontend single-flight behavior is covered by code inspection + documented manual verification (no UI test harness exists).

### User Story 4 - Editing one invoice cannot corrupt another (P1-4)

A user creates invoice A, edits invoice A, closes the modal, then edits invoice B. Invoice B must open with B's data and saving B must not overwrite B with A's or blank fields. The A→B→A round trip must stay correct. The pattern matches the payment/purchase pages (`key`-remount).

**Independent Test**: Component-level re-mount via `key`; manual verification checklist in `quickstart.md` (no UI test framework).

### User Story 5 - Accounting money is Decimal (P1-5)

Journal posting balance checks, ledger running balances, and report aggregation use `Decimal` with exact equality and `0.0000`-quantized output. A one-thousandth imbalance is rejected; an exact fractional balance is accepted; totals across multiple lines are exact.

**Independent Test**: `test_financial_integrity.py` (imbalance-of-one-thousandth rejected, exact fractional accepted, exact ledger running balances, exact trial-balance totals).

### User Story 6 - Every material mutation is auditable (P1-6)

Creation, update, and deactivation of accounts; invitation create/accept/cancel; member role change / removal; sales/purchase/inventory settings changes; invoice/payment/journal/inventory-adjustment create, update, delete (drafts) and posting — each write an immutable, tenant-scoped `AuditLog` row carrying actor, action, target, before/after JSON, and timestamp. Audit rows cannot be updated or deleted; cross-tenant reads are rejected; passwords, refresh tokens, and API keys are never persisted.

**Independent Test**: `backend/apps/core/tests/test_audit_trail.py` (17 tests incl. immutability, isolation, sanitization).

### User Story 7 - Disabled users and suspended tenants lose access immediately (P1-7)

A user disabled at 09:00 is rejected on the next request with an already-issued access token (no wait for expiry). A member of a SUSPENDED/CANCELLED tenant is rejected for that tenant's scope. `/tenants/switch/` refuses a suspended/cancelled tenant. Normal login/refresh behavior is unchanged.

**Independent Test**: `backend/apps/accounts/tests/test_status_enforcement.py` (10 tests) plus the full cross-tenant isolation suite.

## Required Behavior (locked)

- `posted=True` is mandatory for ledger/report aggregation (no permission-gated draft inclusion this pass).
- Balance Sheet carries signed balances; net income/loss is a signed retained-earnings line; nothing is clamped.
- Refresh: save `data.access` **and** `data.refresh`; single-flight via a shared in-flight promise; clear session only on genuine failure.
- Invoice modal: remount form per `editing` identity.
- Audit writes happen **in the service layer** exclusively via `AuditService.record`; no view-layer audit duplication.
- Status enforcement is **centralized** (JWT auth class + shared `TenantScopedPermission` base); no per-endpoint duplication.
- No token-storage redesign (HttpOnly cookies are AUD-009/P2, out of scope). No Feature 013.

## Out of Scope (explicit)

- All P2/P3 findings (AUD-008 through AUD-030) unless strictly required by a P1 fix.
- Feature 013 scope.
- Re-architecture of the accounting model, posting engine, or tenant schema.