# Implementation Tasks: Purchases & Accounts Payable (Feature 011)

Legend: `[ ]` = pending, `[x]` = done (checked off at implementation, not in review).

## Phase 1 â€” Foundation: `apps/purchases` app
- [x] T-001 Backend: create `apps/purchases/apps.py` (`name = "purchases"`), `apps.py` registered; verify `INSTALLED_APPS` entry.
- [x] T-002 Backend: `apps/purchases/models.py` â€” `Vendor`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `PurchaseSettings` per data-model.md (all `TenantScopedModel`).
- [x] T-003 Backend: `apps/purchases/migrations/0001_initial.py` (+ constraints/indexes); `makemigrations --check` clean.

## Phase 2 â€” Generalize `Payment` (sales migration `0003`)
- [x] T-010 Backend: `apps/sales/models.py` â€” add `direction`, `purchase_invoice` (string FK), `invoice` â†’ null, check constraint exactly-one-invoice-reference, index.
- [x] T-011 Backend: `apps/sales/migrations/0003_payment_purchase_direction.py` (depends on purchases `0001`).
- [x] T-012 Backend: `apps/sales/services.py` `PaymentService` â€” `direction` param (default `Receivable`) on create/update; `purchase_paid_amount` / `purchase_outstanding`; Payable branch in `post_payment` (PurchaseSettings, Dr AP / Cr cash, `PAY-PUR-{inv}-{pay}`).
- [x] T-013 Regression: sales payment quickstart + Feature 010 tests still green.

## Phase 3 â€” Purchases services + permissions
- [x] T-020 Backend: `PurchaseSettingsService` (single-row get/update, type-guarded accounts).
- [x] T-021 Backend: `PurchaseInvoiceService` â€” create_draft, update_draft, delete_draft, post_invoice (totals via `compute_line_totals`; AP+Expense required; Input VAT required when `tax > 0`; `PUR-INV-{n}` balanced JE; idempotent).
- [x] T-022 Backend: `apps/purchases/permissions.py` (`CanViewPurchases`, `CanManagePurchases`, `CanPostPurchaseInvoice`, `CanConfigurePurchases`).

## Phase 4 â€” Serializers, views, URLs
- [x] T-030 Backend: serializers â€” `VendorSerializer`, `PurchaseInvoiceLineSerializer`, `PurchaseInvoiceSerializer` (+ paid/outstanding), `PurchaseInvoicePostSerializer`, `PurchasesSettingsSerializer`, `PurchasePaymentSerializer` (+ post serializer), tenant-scoped fields.
- [x] T-031 Backend: views â€” `VendorViewSet`, `PurchaseInvoiceViewSet` (+ `post_invoice`), `PurchasePaymentViewSet` (+ `post_payment`), `PurchaseSettingsViewSet`.
- [x] T-032 Backend: `apps/purchases/urls.py` + `config/urls.py` include â†’ `/api/v1/purchases/`.

## Phase 5 â€” Backend tests
- [x] T-040 Backend: `tests/test_vendors_api.py` (CRUD, duplicate code, deactivate-not-delete, permissions, tenant isolation).
- [x] T-041 Backend: `tests/test_purchase_invoices_api.py` (create/edit/post, totals, immutability, number uniqueness, settings-missing / input-VAT-missing errors, idempotent posting, tenant isolation).
- [x] T-042 Backend: `tests/test_purchase_payments_api.py` (partial/full/multiple, outstanding, overpayment at create+post, Posted-only, draft edit/delete, posted immutability, idempotency, cross-direction guard, tenant isolation).
- [x] T-043 Regression: full `py -m pytest apps/ -q` green (153 baseline + new).

## Phase 6 â€” Frontend
- [x] T-050 Frontend: `frontend/src/services/purchasesService.js`.
- [x] T-051 Frontend: `PurchasesNav.jsx`; routes `/purchases/*` in `App.jsx`.
- [x] T-052 Frontend: `VendorsPage` + `vendors/VendorModal`.
- [x] T-053 Frontend: `PurchaseInvoicesPage` + `invoices/PurchaseInvoiceForm` (line rows, VAT, totals, outstanding).
- [x] T-054 Frontend: `PurchasePaymentsPage` + `payments/PurchasePaymentForm`.
- [x] T-055 Frontend: `PurchasesSettingsPage` (AccountSelect reuse).
- [x] T-056 Frontend: `npm run build` passes; new files lint-clean (16 pre-existing only).

## Phase 7 â€” Docs & close-out
- [x] T-060 Docs: tasks.md all `[x]`, write `report.md`, mark checklists.
- [x] T-061 Meta: AGENTS.md â†’ IMPLEMENTATION COMPLETE; commit via `auto-commit.ps1 after_implement`.


