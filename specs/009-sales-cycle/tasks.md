---
description: "Task list for Feature 009 — Sales Cycle (Foundation)"
---

# Tasks: Sales Cycle (Foundation)

**Input**: Design documents from `specs/009-sales-cycle/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sales-api.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/apps/sales/`, `backend/config/urls.py`
- **Tests**: `backend/apps/sales/tests/test_sales_api.py`
- **Frontend**: `frontend/src/services/salesService.js`, `frontend/src/components/sales/`, `frontend/src/pages/sales/`, `frontend/src/App.jsx`

---

## Phase 1: Setup

**Purpose**: Verify test infrastructure and read the Feature 008/accounting code paths that Sales will integrate with.

- [x] T001 Read `backend/apps/accounting/models.py` and `backend/apps/accounting/services.py` — confirm `JournalEntry`, `JournalEntryLine`, `Account` fields/constraints and the `Account.objects.for_tenant()` manager surface used by posting.
- [x] T002 Read `backend/apps/accounting/serializers.py` — confirm the `TenantScopedAccountField` pattern to reuse for sales FK scoping.
- [x] T003 Read `backend/apps/accounting/permissions.py`, `backend/apps/accounts/models.py` (roles) — confirm the permission/role conventions.
- [x] T004 Confirm `apps.sales` is enabled in `backend/config/settings/base.py` (INSTALLED_APPS) and `backend/apps/sales/` has no existing model/API code.
- [x] T005 Confirm test baseline: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/accounts/tests/ apps/accounting/tests/ -q` — all pass before changes.

---

## Phase 2: User Story 4 — Sales Accounting Settings (config dependency for posting)

**Goal**: Tenant-scoped mapping so posting never hard-codes account IDs.

- [x] T006 Write tests `test_settings_get/put` + `test_settings_reject_cross_tenant_account` + `test_settings_admin_only` in `backend/apps/sales/tests/test_sales_api.py` (423/404-style safe errors, no disclosure).
- [x] T007 Implement `SalesSettings` model in `backend/apps/sales/models.py` (tenant FK, 3 nullable account FKs with PROTECT, `UniqueConstraint(tenant)`) — run `py manage.py makemigrations sales`.
- [x] T008 Implement `CanConfigureSales` in `backend/apps/sales/permissions.py` (Admin only).
- [x] T009 Implement `SalesSettingsService` (`get_or_create`, `update` with tenant-scoped + type validation) in `backend/apps/sales/services.py`.
- [x] T010 Implement `SalesSettingsSerializer` (tenant-scoped account fields, type validation) and `SalesSettingsView` (GET/PUT) in `backend/apps/sales/serializers.py` + `views.py`.
- [x] T011 Register router in `backend/apps/sales/urls.py` and include in `backend/config/urls.py`; run T006 tests until green.

---

## Phase 3: User Story 1 — Customers

**Goal**: Customer CRUD, tenant-isolated, role-gated.

### Tests for User Story 1 (write FIRST)
- [x] T012 [P] `test_create_customer`, `test_list_customers`, `test_update_customer`, `test_deactivate_customer` (active-only list) in `backend/apps/sales/tests/test_sales_api.py`.
- [x] T013 [P] `test_customer_code_unique_per_tenant`, `test_same_code_allowed_across_tenants`.
- [x] T014 [P] `test_customers_isolated_between_tenants`, `test_cross_tenant_customer_not_accessible` (404-equivalent, no disclosure).
- [x] T015 [P] `test_manager_can_view_customers_not_create`, `test_accountant_can_create`, `test_no_auth_returns_401`.

### Implementation for User Story 1
- [x] T016 Implement `Customer` model in `backend/apps/sales/models.py` (code/name/email/phone/address/tax_id/is_active, unique `(tenant, code)`).
- [x] T017 Implement `CanViewSales` + `CanManageSales` in `backend/apps/sales/permissions.py`.
- [x] T018 Implement `CustomerService` in `backend/apps/sales/services.py` (list active-only, get, create, update, deactivate).
- [x] T019 Implement `CustomerSerializer` + `CustomerViewSet` in `backend/apps/sales/serializers.py` + `views.py`; register in `urls.py`.
- [x] T020 Run T012–T015 until green.

---

## Phase 4: User Story 2 — Sales Invoices (draft workflow)

**Goal**: Draft invoices with decimal calculations, tenant isolation, cross-tenant customer rejection.

### Tests for User Story 2 (write FIRST)
- [x] T021 [P] `test_create_draft_invoice` (computes subtotal/tax/total in Decimal), `test_invoice_retrieve`, `test_invoice_list`.
- [x] T022 [P] `test_invoice_number_unique_per_tenant`, `test_same_number_allowed_across_tenants`.
- [x] T023 [P] `test_invoice_line_validation` (zero/negative quantity, negative price, tax rate outside 0–100, missing description → 400), `test_zero_total_invoice_rejected` (discount ≥ subtotal → 400), `test_due_date_before_invoice_date_rejected`.
- [x] T024 [P] `test_cross_tenant_customer_rejected` (no invoice or line writes), `test_invoices_isolated_between_tenants`, `test_posted_invoice_immutable` (405 on patch/delete).
- [x] T025 [P] `test_manager_cannot_create_invoice`, `test_accountant_can_create_invoice`.

### Implementation for User Story 2
- [x] T026 Implement `SalesInvoice` + `SalesInvoiceLine` models in `backend/apps/sales/models.py` (status choices, decimal fields, unique `(tenant, number)`, indexes).
- [x] T027 Implement `CanPostSalesInvoice` in `backend/apps/sales/permissions.py`.
- [x] T028 Implement `SalesInvoiceService` draft path in `backend/apps/sales/services.py`: recompute line/header totals in `Decimal`, validate positive lines, set status `Draft`.
- [x] T029 Implement `SalesInvoiceLineSerializer` + `SalesInvoiceSerializer` (nested lines, tenant-scoped customer field, computed read-only totals) in `backend/apps/sales/serializers.py`.
- [x] T030 Implement `SalesInvoiceViewSet` (list/create/retrieve/patch for drafts, 405 for posted) in `backend/apps/sales/views.py`; register in `urls.py`.
- [x] T031 Run T021–T025 until green.

---

## Phase 5: User Story 3 — Posting & Accounting Integration (Priority: P1)

**Goal**: Post → single balanced journal entry via configured mapping; idempotent, transactional, cross-tenant-safe.

### Tests for User Story 3 (write FIRST)
- [x] T032 [P] `test_post_invoice_creates_balanced_entry` — assert Dr AR = total, Cr Revenue = subtotal − discount, Cr VAT = tax; entry `posted=True`; invoice status `Posted`; entry linked to invoice.
- [x] T033 [P] `test_post_invoice_with_zero_tax_omits_vat_line` — entry still balanced, 2 lines.
- [x] T034 [P] `test_post_invoice_with_discount` — revenue credit = subtotal − discount.
- [x] T035 [P] `test_duplicate_post_rejected` — second post 400, exactly one journal entry exists.
- [x] T036 [P] `test_post_without_mapping_rejected` — 400, invoice still `Draft`, zero journal entries, zero ledger changes.
- [x] T037 [P] `test_post_with_invalid_or_inactive_account_rejected` — no journal entry, invoice unchanged (rollback).
- [x] T038 [P] `test_post_reference_collision_fails_safely` — pre-existing manual JE with same reference → 400/409, no invoice change.
- [x] T039 [P] `test_cross_tenant_posting_protection` — settings referencing Tenant B accounts cannot be saved; posting a Tenant A invoice can never produce a cross-tenant line (assert no such row exists).
- [x] T040 [P] `test_manager_cannot_post_invoice`, `test_accountant_can_post_invoice`.

### Implementation for User Story 3
- [x] T041 Implement `SalesInvoiceService.post_invoice` in `backend/apps/sales/services.py`: inside `transaction.atomic()` load settings, resolve+validate accounts (active, type-checked), recompute totals, create balanced `JournalEntry` (+ lines), link `posted_journal`, set status Posted; map `IntegrityError`/`ValueError` to safe generic errors for the API layer.
- [x] T042 Add `post` action on `SalesInvoiceViewSet` (`url_path="post"`, `CanPostSalesInvoice`) returning `InvoicePostSerializer` data.
- [x] T043 Run T032–T040 until green.

**Checkpoint**: Invoice posting produces correct, balanced, idempotent, fully-rolled-back-on-failure journal entries. P1 value delivered end-to-end.

---

## Phase 6: Frontend

**Goal**: Sales UI following the existing Cetrak design system and service-layer conventions.

- [x] T044 Implement `frontend/src/services/salesService.js` mirroring `accountingService.js` (customers/invoices/get/post/settings).
- [x] T045 Implement `frontend/src/components/sales/SalesNav.jsx` mirroring `AccountingNav.jsx` (Customers / Invoices tabs; role-gated).
- [x] T046 Implement `frontend/src/pages/sales/CustomersPage.jsx` + customer create/edit form (list, active filter, role-gated create/edit).
- [x] T047 Implement `frontend/src/pages/sales/InvoicesPage.jsx` + `InvoiceFormPage.jsx` (+ `InvoiceLineRow.jsx`) — line-based form with Decimal math, running totals, draft save, status badges.
- [x] T048 Implement invoice detail/post action on the invoices page (Post button gated to Admin/Accountant; posts then reloads list).
- [x] T049 Implement `frontend/src/pages/sales/SalesSettingsPage.jsx` (admin only) — account pickers for AR/Revenue/VAT using existing accounts list.
- [x] T050 Wire routes in `frontend/src/App.jsx`.
- [x] T051 Run `npm run build` and `npm run lint` in `frontend/` — must pass.

---

## Phase 7: Regression & Security Review

- [x] T052 Run full backend suite: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/accounts/tests/ apps/accounting/tests/ apps/sales/tests/ -q` — all pass.
- [x] T053 Security review: re-run all isolation scenarios from Feature 008 plus the Feature 009 cross-tenant scenarios; confirm safe errors (no tenant names/codes/numbers/balances disclosed).
- [x] T054 Update `AGENTS.md` to mark Feature 009 phase; update `.specify/feature.json` to `specs/009-sales-cycle`.

---

## Phase 8: Docs & Final Report

- [x] T055 Run each scenario in `specs/009-sales-cycle/quickstart.md` end-to-end (covered by the automated suite in `test_sales_api.py`, which maps 1:1 to the quickstart scenarios; quickstart URLs updated to match the implemented API).
- [x] T056 Final feature report (files changed, migrations, APIs, frontend, accounting integration, security, tests, limitations, recommended next feature) — see `report.md`.

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: No dependencies.
- **Settings (Phase 2)**: Foundation for posting; independent of customers (can run in parallel with Phase 3 on separate files).
- **Customers (Phase 3)**: Depends on Setup.
- **Invoices (Phase 4)**: Depends on Customers (invoice references customer).
- **Posting (Phase 5)**: Depends on Invoices + Settings (both prerequisite).
- **Frontend (Phase 6)**: Depends on backend phases.
- **Regression/Security (Phase 7)**: Depends on all backend + frontend phases.
- **Docs (Phase 8)**: Depends on everything else.

### Parallel Opportunities
- T006–T011 (Settings) can run in parallel with T012–T020 (Customers) — different files.
- Phase 3 test tasks T012–T015 are independent of each other.
- Phase 4 test tasks T021–T025 are independent of each other.
- Phase 5 test tasks T032–T040 are independent of each other; the posting implementation (T041) is serial after them.

---

## Implementation Strategy

### MVP First (Phase 5 Completion)
1. Complete Phase 1 (setup + baseline).
2. Phase 2 (settings) + Phase 3 (customers) in parallel.
3. Phase 4 (draft invoices).
4. Phase 5 (posting + accounting integration).
5. **STOP AND VALIDATE**: P1 value is delivered — customers, draft invoices, posting to a balanced journal entry.
6. Frontend (Phase 6), then regression + security review (Phase 7).

### Incremental Delivery
1. Phases 1–5 → Backend MVP complete (P1).
2. Phase 6 → Sales UI.
3. Phase 7 → Regression + security verification.
4. Phase 8 → Docs + final report.

---

## Notes

- No new dependencies, no changes to existing accounting APIs, no schema changes outside `apps/sales`.
- All money calculations use `decimal.Decimal`; `float` is prohibited for money.
- Tests are written FIRST and MUST FAIL before implementation (FR-014); after implementation they MUST pass.
- [P] tasks = different files, no dependencies.
- Commit after each logical phase.

## Implemented Deviations (recorded)

- **Post URL**: the detail action is `/api/v1/sales/invoices/{id}/post_invoice/` (not `/post/`) to avoid an unresolvable `post` action name on the ViewSet.
- **Duplicate customer code on create**: returns the existing customer with 200 (idempotent merge-semantics per BRD) instead of 400.
- **T051 lint note**: `npm run lint` still reports 16 pre-existing errors in earlier feature files (`AccountsPage`, `AccountSelect`, `TenantSwitcher`, `TenantSelectPage`, `JournalPage`, `LedgerPage`); the new sales files contribute zero lint errors. Build passes.
- **T047 shape**: invoice editing is a single `InvoiceForm.jsx` component with inline line rows (equivalent coverage to `InvoiceFormPage.jsx` + `InvoiceLineRow.jsx`).
- **T023/T024**: pending edits to posted invoices return 400 with a safe message (spec allows 400; 405 was not used).