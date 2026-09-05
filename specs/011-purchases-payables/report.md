# Feature 011 — Purchases & Accounts Payable: Final Report

Status: IMPLEMENTATION COMPLETE — all backend tests passing, frontend builds, new files lint-clean.

## Summary

Implemented Purchases & Accounts Payable — the purchasing-side equivalent of Features 009 + 010,
reusing the existing architecture rather than duplicating it. A vendor → purchase invoice →
accounts payable → payment → journal entry workflow sits next to sales:

- **Purchase invoices** record vendor purchases (free-text line items, per-line VAT, header
  discount) and post atomically to a single balanced Journal Entry — **Dr configured Expense,
  Dr configured Input VAT (when `tax > 0`), Cr configured Accounts Payable** — with reference
  `PUR-INV-{number}`.
- **Vendor payments** apply against **posted** purchase invoices and post the reverse AP cash
  entry — **Dr Accounts Payable, Cr the payment's cash/bank Asset account** — with reference
  `PAY-PUR-{invoice.number}-{payment.number}`.
- The Feature 010 `Payment` model/service is **generalized** with a `direction` field
  (`Receivable`/`Payable`, default `Receivable`) so receipts and vendor payments share one
  engine. The sales payments API is unchanged; no sales or accounting behavior changed.

Posting is idempotent (status guard + unique reference), row-locked (`select_for_update` on the
invoice) to defeat concurrent overpayment, tenant-scoped end to end, and uses
`Decimal(19,4)` only.

## Files Changed / Added

### Backend (new — `apps/purchases`)
- `models.py` — `Vendor` (tenant-unique `code`, contact, `tax_id`, `is_active`), `PurchaseInvoice`
  (number, vendor, dates, discount/subtotal/tax/total, status Draft/Posted, `posted_journal`,
  unique `(tenant, number)`), `PurchaseInvoiceLine` (description, qty, unit_price, tax_rate,
  computed subtotal/tax/total `Decimal(19,4)`), `PurchaseSettings` (single row per tenant:
  `accounts_payable` Liability, `expense_account` Expense, `input_vat` Asset).
- `migrations/0001_initial.py` — generated (with constraints/indexes).
- `permissions.py` — `CanViewPurchases`, `CanManagePurchases`, `CanPostPurchaseInvoice`,
  `CanConfigurePurchases` (role matrix mirrors sales: Admin/Accountant manage + post, Manager
  view-only, Admin-only configure).
- `services.py` — `PurchaseSettingsService` (single-row get/update, type-guarded accounts);
  `PurchaseInvoiceService` (`create_draft`, `update_draft`, `delete_draft`, `post_invoice`).
- `serializers.py` — `VendorSerializer`, `PurchaseSettingsSerializer` (+ `*_name` fields),
  `PurchaseInvoiceSerializer` (+ additive `paid_amount`/`outstanding_balance`),
  `PurchaseInvoicePostSerializer`, `PurchasePaymentSerializer` (nested purchase-invoice summary
  incl. vendor/total/paid/outstanding); tenant-scoped PK fields.
- `views.py` — `VendorViewSet`, `PurchaseInvoiceViewSet` (+ `post_invoice` action),
  `PurchasePaymentViewSet` (+ `post_payment` action), `PurchaseSettingsViewSet`; per-action
  permissions; `?status=` filters.
- `urls.py` — basenames `vendor`, `purchase-invoice`, `purchase-payment` (distinct from sales'
  `invoice`/`payment` to avoid `reverse()` ambiguity).
- `tests/base.py` + `test_vendors_api.py` (12), `test_purchase_invoices_api.py` (25),
  `test_purchase_payments_api.py` (33) — **70 tests**.

### Backend (modified)
- `apps/sales/models.py` — `Payment` generalized: `direction` (`Receivable`/`Payable`, default
  Receivable), `invoice` now nullable, `purchase_invoice` string FK to `apps.purchases`,
  `CheckConstraint` exactly-one-invoice-reference, index.
- `apps/sales/migrations/0003_payment_purchase_direction.py` — renamed from the auto-generated
  name; depends on `apps.purchases` `0001`.
- `apps/sales/services.py` — `PaymentService` extended: `direction` param (default Receivable)
  on create/update (no sales call-site changes), `purchase_paid_amount`/`purchase_outstanding`,
  Payable branch of `post_payment` (PurchaseSettings + type checks, Dr AP / Cr cash,
  `PAY-PUR-…` reference).
- `backend/config/urls.py` — includes `api/v1/purchases/`.

### Frontend (new)
- `src/services/purchasesService.js` — vendors/invoices/payments/settings actions.
- `src/components/Layout/PurchasesNav.jsx` — Vendors / Purchase Invoices / Payments /
  Settings (Admin).
- `src/pages/purchases/{VendorsPage,PurchaseInvoicesPage,PurchasePaymentsPage,
  PurchasesSettingsPage}.jsx`.
- `src/components/purchases/vendors/VendorModal.jsx`,
  `src/components/purchases/invoices/PurchaseInvoiceForm.jsx`,
  `src/components/purchases/payments/PurchasePaymentForm.jsx` (posted-only picker with
  outstanding, client-side overpayment guard, Asset cash-account select; reuses
  `AccountSelect`).

### Frontend (modified)
- `src/App.jsx` — routes `/purchases/vendors|invoices|payments|settings` (all protected).

### Docs
- `specs/011-purchases-payables/{tasks.md,checklists/requirements.md}` — marked complete.
- `specs/011-purchases-payables/report.md` (this file).
- `AGENTS.md` — phase marker updated to Feature 011 IMPLEMENTATION COMPLETE.

## Migrations

- `apps.purchases.0001_initial` — vendors, purchase invoices (lines + posted_journal), purchase
  settings; unique `(tenant, number)`; FK PROTECT (vendor, accounts).
- `apps.sales.0003_payment_purchase_direction` — additive: `direction` (default Receivable),
  nullable `invoice`, `purchase_invoice` string FK, exactly-one-invoice check, index.
  `makemigrations --check --dry-run` and `migrate --check` both clean.

## API Surface (`api/v1/purchases/`)

| Endpoint | Method | Permission | Notes |
|---|---|---|---|
| `vendors/` | GET/POST | View/Manage | idempotent code create (200 if exists), `?is_active=` |
| `vendors/{id}/` | GET/PATCH/DELETE | View/Manage/Manage | delete → 400 if invoices, else 204 deactivate |
| `invoices/` | GET/POST | View/Manage | `?status=`; draft with lines + VAT |
| `invoices/{id}/` | GET/PATCH/DELETE | View/Manage/Manage | drafts only for PATCH/DELETE |
| `invoices/{id}/post_invoice/` | POST | PostPurchaseInvoice | balanced `PUR-INV-{n}` JE |
| `payments/` | GET/POST | View/Manage | Payable only; `?status=`, `?purchase_invoice=` |
| `payments/{id}/` | GET/PATCH/DELETE | View/Manage/Manage | drafts only for PATCH/DELETE |
| `payments/{id}/post_payment/` | POST | PostPurchaseInvoice | Dr AP / Cr cash `PAY-PUR-…` JE |
| `settings/current/` | GET/PUT | Configure (Admin) | get-or-create row; type-guarded accounts |

Sales endpoints (`api/v1/sales/*`) are unchanged.

## Accounting Integration

Posting (inside `transaction.atomic()`, invoice row locked with `select_for_update`, idempotent
via status guard + `(tenant, reference)` unique):

- **Purchase invoice**: requires Settings with active same-tenant AP (Liability) + Expense;
  Input VAT (Asset) additionally **required when `tax > 0`** (a deviation from sales' optional
  VAT — sales unchanged). Entry `reference = "PUR-INV-{number}"`, `date = invoice_date`; lines
  `Dr expense (subtotal − discount)`, `Dr input_vat (tax, when > 0)`, `Cr accounts_payable
  (total)`. Balanced by construction.
- **Vendor payment**: requires Settings AP (Liability); entry `reference =
  "PAY-PUR-{invoice.number}-{payment.number}"`, `date = payment_date`; lines `Dr
  accounts_payable`, `Cr cash_account` (each = amount). Outstanding recomputed under the row
  lock; overpayment → 400 with zero journal entries.
- Money stays `Decimal(19,4)` end to end; no `float`.

## Frontend

Purchases UI follows the existing design system (inline styles, `Table`/`Modal`/`Button`/
`Input`, `AccountSelect`). Role gating mirrored on the client; server 403s authoritative. The
payment picker lists posted invoices with live outstanding; forms block client-side
overpayment before hitting the API. `npm run build` passes. Lint: the 16 remaining `npm run
lint` problems (15 errors + 1 warning) are all pre-existing in earlier feature files; the new
purchases files add zero lint problems (fetches use the promise-chained `.then/.catch/.finally`
pattern to avoid `set-state-in-effect`).

## Security

- Every query scoped via `objects.for_tenant(request.tenant_id)`; cross-tenant lookups 404
  (no disclosure).
- Settings and posting re-validate account tenant, `is_active`, and type (Liability/Expense/
  Asset) at post time — defense in depth.
- Purchases permission classes gate the API; a Manage user cannot post and a Manager cannot
  write.
- Safe errors: posting/settings failures never surface account or tenant names.

## Tests

- 223 backend tests pass: 153 pre-existing + 70 new (12 vendors, 25 purchase invoices, 33
  purchase payments).
  Command: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/ -q`
- Coverage includes: balanced-JE posting with VAT, partial/full/multiple payments, outstanding
  math, overpayment at create and post, idempotent posting, draft edit/delete + posted
  immutability, input-VAT-required-when-taxed, settings-missing/invalid, cross-tenant
  injection, **sales payment regression** (Receivable JE unchanged, refs never overlap),
  role matrix, no-disclosure.

## Recorded Deviations

1. **Accounting direction (brief → authoritative)**: the original brief illustrated purchase
   payments as "Cr AP / Dr cash"; the implemented (correct) JE is **Dr AP / Cr cash** — money
   leaves the business, AP falls. Documented and locked in the plan.
2. **Settings endpoint** uses `PUT` (mirrors sales), not the draft contract's `POST`.
3. **Vendor delete** returns `400` ("Vendor has purchase invoices and cannot be deleted.
   Deactivate instead.") when invoices exist and `204` (deactivate) otherwise — mirrors the
   Feature 009 customer rule; the draft contract said `204` always.
4. **Input VAT required when `tax > 0`** at posting (balanced-JE invariant); sales' optional-VAT
   path is untouched.
5. Vendor list supports `?is_active=` (no `?search=`); invoice/payment list filters are
   `?status=` / `?purchase_invoice=` as built.
6. Draft-edit/delete of posted resources returns `400` (DRF `ValidationError`), not `403`;
   permission-denied remains `403`.

## Limitations / Follow-ups (deferred, per spec)

- Cancelled / void purchase invoices (posting undo) — manual reversing JE is the documented
  correction path; sales convention preserved.
- Payment reversal — deferred.
- Per-line account mapping, header-level VAT entry, auto-sequenced numbers — deferred (user
  supplies numbers, unique per tenant).
- Inventory / COGS split and item references (Feature 012).
- AP aging by due date / vendor statements — recommended next feature alongside AR aging.

## Recommended Next Feature

Vendor statements / AP aging (per-vendor outstanding rollup, due-date aging), or Feature 012
inventory/COGS, or editing/reversing posted entries in the accounting ledger.