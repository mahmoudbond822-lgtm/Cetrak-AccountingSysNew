# Implementation Plan: Purchases & Accounts Payable (Feature 011)

## Goal

Introduce the purchasing domain — **Vendors → Purchase Invoices → Accounts Payable → Payments → Journal Entry** — as the purchasing-side equivalent of Features 009 + 010, by (a) generalizing Feature 010's `Payment` to a `direction`-aware model so vendor payments reuse the same engine, and (b) building a new symmetric `apps/purchases` app (vendors, purchase invoices, purchase settings). Account mappings come from a new `PurchaseSettings` (mirror of `SalesSettings`); posting is atomic, row-locked, idempotent, and tenant-isolated.

## Constraints (from spec + Constitution)

- Money = `Decimal(19,4)`; **no `float` in any money path**; reuse `sales.services.compute_line_totals`.
- `transaction.atomic()` around every posting; `select_for_update()` on the invoice row at payment post; unique `(tenant, reference)` as the idempotency backstop.
- Tenant isolation on every read via `.for_tenant(request.tenant_id)`; generic errors on cross-tenant references (no disclosure).
- **No changes** to `apps/accounting` schema, `SalesSettings`, or the sales payments API. Feature 009/010 must remain passing unchanged.
- No hard-coded account/tenant IDs. New accounts all come from tenant settings.
- No new roles; purchases permissions mirror sales. No new frontend dependencies.
- `apps.purchases` already exists in `INSTALLED_APPS` (empty scaffold).

## Key design decisions (locked)

| # | Decision |
|---|---|
| D1 | New `apps/purchases` app (already registered) |
| D2 | New `PurchaseSettings` mirror; do **not** generalize `SalesSettings` |
| D3 | **Generalize** the `Payment` model/service (`direction = Receivable \| Payable`); sales API unchanged |
| D4 | Purchase invoice lifecycle `Draft → Posted`; cancelled/void deferred |
| D5 | Purchase posting JE `PUR-INV-{n}`: Dr Expense net, Dr Input VAT tax (required when tax>0), Cr AP total |
| D6 | Payable payment JE `PAY-PUR-{inv}-{pay}`: **Dr AP, Cr cash** (deviation: correct AP settlement direction) |
| D7 | Input VAT account typed **Asset**; AP=**Liability**; Expense=**Expense** |
| D8 | User-supplied numbers unique per tenant (invoice + payment) |
| D9 | Permissions: `CanViewPurchases`, `CanManagePurchases`, `CanPostPurchaseInvoice`, `CanConfigurePurchases` |
| D10 | APIs live at `/api/v1/purchases/` (vendors, invoices, payments, settings) |

Concurrency and security follow the Feature 010 winning pattern exactly (row lock + unique reference + atomic).

## Phases

### Phase 1 — Foundation: `apps/purchases` app + models + migration `0001_initial`
- `apps.py` (name `purchases`), `admin.py` (optional), package init already present.
- `models.py`: `Vendor`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `PurchaseSettings` per data-model.md.
- `migrations/0001_initial.py`.
- POST/GET sanity: `makemigrations --check` clean.

### Phase 2 — Generalize `Payment` (sales migration `0003`)
- `apps/sales/models.py`: add `direction`, `purchase_invoice` (string FK), alter `invoice` to null, add check constraint + index.
- `apps/sales/migrations/0003_payment_purchase_direction.py` (depends on purchases `0001`).
- `apps/sales/services.py` `PaymentService`: add `direction` param (default Receivable) to `create_draft`/`update_draft`; add `purchase_paid_amount`/`purchase_outstanding`; extend `post_payment` with the Payable branch (PurchaseSettings, Dr AP/Cr cash, `PAY-PUR-…`).
- Existing sales methods/paths behave identically (regression gate).

### Phase 3 — Purchases services + settings
- `services.py`: `PurchaseSettingsService` (type-guarded get/update), `PurchaseInvoiceService` (create_draft/update_draft/delete_invoice/post_invoice, totals via `compute_line_totals`, input-VAT-required-when-tax>0).
- Permissions (`permissions.py`).

### Phase 4 — Serializers + views + URLs
- Serializers: `VendorSerializer`, `PurchaseInvoiceLineSerializer`, `PurchaseInvoiceSerializer` (+ additive paid/outstanding), `PurchaseInvoicePostSerializer`, `PurchasesSettingsSerializer`, `PurchasePaymentSerializer` (direction=Payable), tenant-scoped vendor/posted-invoice fields.
- Views: `VendorViewSet`, `PurchaseInvoiceViewSet` (+ `post_invoice` action), `PurchasePaymentViewSet` (+ `post_payment`), `PurchaseSettingsViewSet`.
- URLs registered under `api/v1/purchases/`; `config/urls.py` include.

### Phase 5 — Backend tests (`apps/purchases/tests/`)
- `test_vendors_api.py`, `test_purchase_invoices_api.py` (incl. posting matrix), `test_purchase_payments_api.py` (incl. cross-direction guard + tenant isolation).
- Full regression: `py -m pytest apps/ -q` (baseline 153 + new all green).

### Phase 6 — Frontend
- `frontend/src/services/purchasesService.js`.
- `PurchasesNav.jsx` (Vendors / Purchase Invoices / Payments / Settings).
- Pages/components: `VendorsPage` + `vendors/VendorModal`; `PurchaseInvoicesPage` + `invoices/PurchaseInvoiceForm`; `PurchasePaymentsPage` + `payments/PurchasePaymentForm`; `PurchasesSettingsPage` (AccountSelect reuse).
- Routes `/purchases/vendors|invoices|payments|settings` in `App.jsx`.
- `npm run build` passes; new files lint-clean (16 pre-existing only).

### Phase 7 — Docs & close-out
- tasks.md `[x]`, report.md, checklists, AGENTS.md → IMPLEMENTATION COMPLETE; commit via `auto-commit.ps1`.

## Sanity check: JE balance (purchase example from brief, net 10,000 + VAT 1,500)

- Posting: Dr Expense 10,000.0000 + Dr Input VAT 1,500.0000 = 11,500.0000 ; Cr AP 11,500.0000 → balanced.
- Payment 11,500: Dr AP 11,500.0000 ; Cr Cash 11,500.0000 → balanced. Outstanding = 0.

## Risks

See research §3 (payment-model generalization regression, import cycles, VAT-missing imbalance, concurrency). Managing changes are exactly the Feature 010 guards (row lock, reference uniqueness, status + OneToOne guards), plus the new DB check constraint for exactly-one invoice reference.

## Definition of Done

1. `makemigrations --check --dry-run` clean after both migrations.
2. Vendor CRUD + uniqueness + tenant isolation green.
3. Purchase invoice draft→posted, immutable after posting, one balanced `PUR-INV-{n}` JE, idempotent.
4. Payments: partial/full/multiple (20,000 → 7,000 → 13,000) correct; overpayment never booked; Dr AP / Cr cash JE; idempotent.
5. Cross-tenant vendor/invoice/account/payment denied with generic errors.
6. Full backend suite green (153 baseline + new).
7. Frontend build green; new files lint-clean.
8. Spec artifacts complete, committed, AGENTS.md updated.