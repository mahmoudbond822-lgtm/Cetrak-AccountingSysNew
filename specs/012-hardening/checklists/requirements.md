# Spec Quality Checklist: 012-H Production Hardening

Verified at close-out against `.specify/memory/constitution.md` and AUD-001.

## Requirement completeness

- [x] P1-1 draft JEs excluded from ledger, trial balance, income statement, balance sheet — tested.
- [x] P1-1 Journal UI has real Save Draft → Post flow — implemented + verified.
- [x] P1-1 posted JE remains balanced and immutable — tested.
- [x] P1-2 balance sheet balances in net profit, loss, and break-even periods — tested.
- [x] P1-2 negative balances are not hidden — tested.
- [x] P1-3 rotated refresh token persisted and old token not reused — tested (backend) + code-inspected (frontend).
- [x] P1-3 concurrent 401s share one refresh op — single-flight promise.
- [x] P1-3 genuine refresh failure logs the user out — implemented.
- [x] P1-4 invoice modal resets between records; no stale/blank overwrite — `key` remount + manual verification.
- [x] P1-5 Decimal throughout accounting money math; no float; exact equality — tested.
- [x] P1-6 audit log exists; tenant/actor/action/target/timestamp recorded — tested.
- [x] P1-6 important mutations audited (accounts, membership, settings, financial documents) — tested.
- [x] P1-6 audit records immutable (no update/delete/bulk) — tested.
- [x] P1-6 secrets never logged — tested.
- [x] P1-7 disabled users rejected on active sessions — tested.
- [x] P1-7 suspended/cancelled tenants rejected, incl. `/tenants/switch/` — tested.
- [x] P1-7 normal login/refresh/tenant-isolation intact — full suite green.

## Regression gates

- [x] Full backend suite: `324 passed, 1 skipped` (≥ 274 baseline preserved).
- [x] `py manage.py makemigrations --check --dry-run` → "No changes detected".
- [x] `npm run build` — pass.
- [x] `npm run lint` — 16 problems, identical to pre-existing baseline; zero new.
- [x] Tenant isolation suite green (cross-tenant matrix preserved).

## Governance / scope

- [x] No Feature 013 created; no product scope added.
- [x] No unrelated P2/P3 implementation (only P1-scoped changes; pre-existing HEAD items verified).
- [x] No push / no deploy (per AGENTS.md constraint).
- [x] Changes restricted to hardening scope; working-tree diff inspected before commit.
- [x] Constitution impact documented in `report.md` and the hardening report.