# Implementation Tasks: Purchases & Accounts Payable (Feature 011)

Legend: `[ ]` = pending, `[x]` = done (checked off at implementation, not in review).

## Phase 1 — Foundation: `apps/purchases` app
- [ ] T-001 Backend: create `apps/purchases/apps.py` (`name = "purchases"`), `apps.py` registered; verify `INSTALLED_APPS` entry.
- [ ] T-002 Backend: `apps/purchases/models.py` — `Vendor`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `PurchaseSettings` per data-model.md (all `TenantScopedModel`).
- [ ] T-003 Backend: `apps/purchases/migrations/0001_initial.py` (+ constraints/indexes); `makemigrations --check` clean.

## Phase 2 — Generalize `Payment` (sales migration `0003`)
- [ ] T-010 Backend: `apps/sales/models.py` — add `direction`, `purchase_invoice` (string FK), `invoice` → null, check constraint exactly-one-invoice-reference, index.
- [ ] T-011 Backend: `apps/sales/migrations/0003_payment_purchase_direction.py` (depends on purchases `0001`).
- [ ] T-012 Backend: `apps/sales/services.py` `PaymentService` — `direction` param (default `Receivable`) on create/update; `purchase_paid_amount` / `purchase_outstanding`; Payable branch in `post_payment` (PurchaseSettings, Dr AP / Cr cash, `PAY-PUR-{inv}-{pay}`).
- [ ] T-013 Regression: sales payment quickstart + Feature 010 tests still green.

## Phase 3 — Purchases services + permissions
- [ ] T-020 Backend: `PurchaseSettingsService` (single-row get/update, type-guarded accounts).
- [ ] T-021 Backend: `PurchaseInvoiceService` — create_draft, update_draft, delete_draft, post_invoice (totals via `compute_line_totals`; AP+Expense required; Input VAT required when `tax > 0`; `PUR-INV-{n}` balanced JE; idempotent).
- [ ] T-022 Backend: `apps/purchases/permissions.py` (`CanViewPurchases`, `CanManagePurchases`, `CanPostPurchaseInvoice`, `CanConfigurePurchases`).

## Phase 4 — Serializers, views, URLs
- [ ] T-030 Backend: serializers — `VendorSerializer`, `PurchaseInvoiceLineSerializer`, `PurchaseInvoiceSerializer` (+ paid/outstanding), `PurchaseInvoicePostSerializer`, `PurchasesSettingsSerializer`, `PurchasePaymentSerializer` (+ post serializer), tenant-scoped fields.
- [ ] T-031 Backend: views — `VendorViewSet`, `PurchaseInvoiceViewSet` (+ `post_invoice`), `PurchasePaymentViewSet` (+ `post_payment`), `PurchaseSettingsViewSet`.
- [ ] T-032 Backend: `apps/purchases/urls.py` + `config/urls.py` include → `/api/v1/purchases/`.

## Phase 5 — Backend tests
- [ ] T-040 Backend: `tests/test_vendors_api.py` (CRUD, duplicate code, deactivate-not-delete, permissions, tenant isolation).
- [ ] T-041 Backend: `tests/test_purchase_invoices_api.py` (create/edit/post, totals, immutability, number uniqueness, settings-missing / input-VAT-missing errors, idempotent posting, tenant isolation).
- [ ] T-042 Backend: `tests/test_purchase_payments_api.py` (partial/full/multiple, outstanding, overpayment at create+post, Posted-only, draft edit/delete, posted immutability, idempotency, cross-direction guard, tenant isolation).
- [ ] T-043 Regression: full `py -m pytest apps/ -q` green (153 baseline + new).

## Phase 6 — Frontend
- [ ] T-050 Frontend: `frontend/src/services/purchasesService.js`.
- [ ] T-051 Frontend: `PurchasesNav.jsx`; routes `/purchases/*` in `App.jsx`.
- [ ] T-052 Frontend: `VendorsPage` + `vendors/VendorModal`.
- [ ] T-053 Frontend: `PurchaseInvoicesPage` + `invoices/PurchaseInvoiceForm` (line rows, VAT, totals, outstanding).
- [ ] T-054 Frontend: `PurchasePaymentsPage` + `payments/PurchasePaymentForm`.
- [ ] T-055 Frontend: `PurchasesSettingsPage` (AccountSelect reuse).
- [ ] T-056 Frontend: `npm run build` passes; new files lint-clean (16 pre-existing only).

## Phase 7 — Docs & close-out
- [ ] T-060 Docs: tasks.md all `[x]`, write `report.md`, mark checklists.
- [ ] T-061 Meta: AGENTS.md → IMPLEMENTATION COMPLETE; commit via `auto-commit.ps1 after_implement`.