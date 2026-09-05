# Technical Research: Purchases & Accounts Payable

## Objective

Determine how to introduce the purchasing domain (Vendors, Purchase Invoices, Accounts Payable, payments to vendors) that integrates with the existing Accounting core — reusing Features 009/010 architecture instead of duplicating it, and without breaking the shipped sales/payments behavior.

## 1. Existing Architecture Surveyed

### 1.1 Accounting core (`apps/accounting`)
- `Account` (`TenantScopedModel`): `Type` = Asset/Liability/Equity/Revenue/Expense; `is_active`; parent hierarchy. Cash/bank accounts are **Asset**.
- `JournalEntry`: `date`, `description`, `reference` (unique per tenant), `posted`, `posted_at`; `is_balanced`.
- `JournalEntryLine`: `account` FK PROTECT, `debit`/`credit` Decimal(19,4).
- **LedgerService running balance = debit − credit**. So reducing an Asset (cash out) is a **credit**; reducing a Liability (paying a vendor) is a **debit**.

### 1.2 Sales domain (`apps/sales`, Features 009 + 010)
- `SalesInvoiceService.post_invoice`: validates settings → atomic `transaction.atomic()` → single balanced JE, reference `SALES-INV-{number}`, marks Posted. Idempotent via status guard + `(tenant, reference)` unique.
- `Payment` (Feature 010): draft→posted, `cash_account` Asset, JE `PAY-INV-{invoice.number}-{payment.number}` — Dr cash, Cr settings-AR. Outstanding = total − Σ posted; `select_for_update` row lock during posting; idempotency guard; `IntegrityError` → duplicate error. **All tests exercise the API, not direct model wiring** → the model can be generalized safely.
- `SalesSettings`: single-row-per-tenant account mapping (AR, Revenue, VAT-payable) with a guarded service.
- `SalesSettingsService.update` type-guards each mapping; `TenantScopedAccountField` validates tenant scoping at the serializer layer.
- `compute_line_totals(quantity, unit_price, tax_rate)` in `sales/services.py` — shared line math (a purchase line uses the identical formula).
- Permissions (`CanViewSales`, `CanManageSales`, `CanPostSalesInvoice`, `CanConfigureSales`); serializers/views/services layered with `self.tenant_id = request.tenant_id`.

### 1.3 Domain symmetry (the key insight)

| Concept | Sales (AR) | Purchases (AP) |
|---|---|---|
| Counterparty | `Customer` | `Vendor` |
| Document | `SalesInvoice` | `PurchaseInvoice` (+ lines) |
| Balance account | `SalesSettings.accounts_receivable` (Asset) | `PurchaseSettings.accounts_payable` (Liability) |
| Invoice JE | Dr AR, Cr Revenue, Cr VAT-payable | Dr Expense, Dr VAT-input, Cr AP |
| Payment direction | Receivable (Dr cash, Cr AR) | Payable (Dr AP, Cr cash) |
| Payment reference | `PAY-INV-{inv}-{pay}` | `PAY-PUR-{inv}-{pay}` |

The document lifecycle, totals engine, posting recipe (`transaction.atomic`, row-lock, idempotent reference), serializer/field and view patterns are **structurally identical**.

## 2. Design Decisions

### D1 — Where does the purchasing domain live?
New app **`apps/purchases`** (`purchases` already exists in `INSTALLED_APPS` as an empty scaffold with `apps/purchases/__init__.py`). Tables `purchase_vendor`, `purchase_invoice`, `purchase_invoiceline`, `purchase_settings`; migration `0001_initial`. Keeps the AR/AP domains symmetric and gives Feature 012 Inventory a sibling home. No other app changes (only `config/urls.py` gains the `api/v1/purchases/` include).

### D2 — Purchase account mapping: new `PurchaseSettings`, not a generalized "AccountingSettings"
Evaluated generalizing `SalesSettings` into one shared mapping table (e.g. a `scope` field + FK set). **Rejected**: the two domains genuinely differ (AR+Revenue+VAT-payable vs AP+Expense+VAT-input), the churn in `SalesSettings`, its serializer/views/tests, and the risk to Feature 009 outweigh the cosmetic DRY gain. A **new `PurchaseSettings` that mirrors SalesSettings exactly** (single row per tenant, three type-guarded account FKs) is additive, zero-risk, and consistent with the constitution's MVP discipline.

Account types enforced in the service and serializer:
- `accounts_payable` → **Liability**
- `expense_account` → **Expense**
- `input_vat` → **Asset** (recoverable/input VAT receivable — money the business will recover; documented as a deliberate choice — mirror price-exclusive tax conventions).

### D3 — Payment generalization (required by the brief)
The brief explicitly says: prefer reuse/generalization, do NOT blindly duplicate the payments implementation. Decision: **generalize the single `Payment` model + `PaymentService`** in `apps/sales`:

Model additions (table stays `sales_payment`; migration `sales 0003`):
1. `direction` = `Receivable | Payable`, default `Receivable`.
2. `invoice` FK → `null=True` (Receivable case) — column is now nullable.
3. `purchase_invoice` FK → `"purchases.PurchaseInvoice"` (PROTECT, `related_name="payments"`, lazy string reference — no import cycle), null for Receivable.
4. `CheckConstraint` `check_payment_invoice_reference`: exactly one of `invoice` / `purchase_invoice` is non-null.
5. Index on `purchase_invoice`.

`PaymentService` dispatch (all existing sales method signatures preserved — sales views pass nothing new):
- `create_draft(..., direction="Receivable", invoice_id=...)` resolves the invoice per direction. Add `purchase_paid_amount(purchase_invoice)` / `purchase_outstanding(purchase_invoice)`.
- `post_payment` reads `payment.direction`:
  - **Receivable** (unchanged path): settings = `SalesSettings`; validate AR; reference `PAY-INV-…`; Dr cash, Cr AR.
  - **Payable**: settings = `PurchaseSettings` (lazy import to stay decoupled); validate AP (tenant, active, Liability); row-lock `PurchaseInvoice`; recompute outstanding over posted Payable payments; reference `PAY-PUR-{inv.number}-{pay.number}`; **Dr AP, Cr cash** (correct AP settlement); link+Posted.

Imports are safe (no cycle): `apps.purchases.models` does not import `apps.sales`; `apps.purchases.services` imports `sales.services.compute_line_totals`; `sales.services` imports `purchases.models`. `sales.models` references the purchase invoice FK as a **string** (`"purchases.PurchaseInvoice"`) so model-loading order is irrelevant.

Two serializers/viewsets over the one model/service keep each API surface clean: sales `PaymentSerializer`/`PaymentViewSet` (unchanged) and `purchases` `PurchasePaymentSerializer`/`PurchasePaymentViewSet` (direction=Payable, purchases permissions). The bulk of the logic — outstanding computation, overpayment guard, row-locked atomic posting, idempotency — is shared in `PaymentService`.

### D4 — Purchase invoice lifecycle
`Draft → Posted` only, mirroring sales. Draft: editable/deletable, no ledger impact. Posted: immutable; `posted_journal` OneToOne set at posting. **Cancelled/Void deferred** (FR-018): sales never added it, and "unpaid when cancelled" is already satisfied because only Posted invoices accept payments. Deferring keeps posting/immutability semantics uniform and avoids reversal machinery — consistent with the Feature 010 "reversal deferred" decision. Documented as a future capability.

### D5 — Posting a purchase invoice
Mirror `post_invoice`:
- Status guard (Draft only).
- Settings guard: AP + Expense accounts required (tenant, active, correct type). **Input VAT required if `tax > 0`** — this keeps the JE balanced by construction. (Note: sales posts an unbalanced JE if `tax > 0` but `vat_payable` is unset; that is a latent sales limitation, out of scope here, and NOT copied.)
- Atomic: create `JournalEntry` (reference `PUR-INV-{number}`, `date=invoice_date`, `posted=True`) + lines: Dr expense = subtotal − discount; Dr input_vat = tax (only when > 0); Cr AP = total. Mark Posted.
- `IntegrityError` → `ValueError("Journal entry reference already exists.")`.

### D6 — Outstanding AP and overpayment prevention
Identical to Feature 010: `paid = Σ posted Payable payments`, `outstanding = max(total − paid, 0)`. Rejected at serializer **and** under `select_for_update` inside the posting transaction (authoritative). AP can never go negative.

### D7 — Serializer/field reuse
- `TenantScopedAccountField` reused for all settings/cash-account fields.
- `TenantScopedVendorField`, `TenantScopedPostedPurchaseInvoiceField` mirror the sales fields.
- `PurchaseInvoiceSerializer` mirror of `SalesInvoiceSerializer` including additive `paid_amount`/`outstanding_balance` computed through `PaymentService.purchase_*`.
- `PurchasesSettingsSerializer` mirror of `SalesSettingsSerializer`.

### D8 — Errors (no disclosure)
Same wording family as sales: "Vendor not found.", "Invoice not found.", "Purchase accounting settings are not configured.", "Account must be of type …,", "Invoice number already exists.", "Journal entry reference already exists.", "Amount exceeds the outstanding balance.", "Payment number already exists.". Tests assert stable substrings.

### D9 — Permissions
`apps/purchases/permissions.py` mirrors sales exactly (Admin/Accountant/Manager vs Admin/Accountant vs Admin). No new roles. Posting purchases = `CanPostPurchaseInvoice`; payment posting for Payable = same permission (parallel to `CanPostSalesInvoice` covering payment posting on the AR side).

## 3. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Breaking Feature 010 by generalizing `Payment` | `direction` defaults Receivable; existing columns unchanged except `invoice` becoming nullable (no column rename); sales quickstart/tests re-run; API shape identical; new fields additive. |
| Circular imports (sales ↔ purchases) | `purchases.models` never imports sales; FKs to purchases use string references; `purchases.services` imports only `sales.services.compute_line_totals`. |
| Input VAT type mismatch / left-as-Liability confusion | Enforced `Asset` at service+serializer; documented as a deliberate accounting treatment choice. |
| Unbalanced JE if VAT account missing | Posting **requires** Input VAT when `tax > 0` (stricter than sales — documented deviation). |
| Concurrent payment / invoice posting races | `select_for_update` on the invoice row + unique `(tenant, reference)` backstop, both inside `transaction.atomic()` (Feature 010 pattern). |
| Duplicate posting | Status guard + reference uniqueness + idempotency tests for invoice and payment. |
| Cross-tenant vendor/invoice/account leakage | `.for_tenant()` everywhere; tenant-scoped serializer fields; generic errors; P0 test matrix. |
| Money drift | Decimal(19,4) end-to-end, only Decimal math in services; `compute_line_totals` shared; no float conversions. |
| UI regressions / lint | Mirror 009/010 pages/forms; promise-chained fetches (no sync setState in effects) so new files stay lint-clean; only the documented 16 pre-existing lint issues allowed. |
| Over-engineering cancellation/inventory | Cancelled/Void and item FKs explicitly deferred (FR-018, assumptions); Inventory reserved for Feature 012. |

## 4. Non-Goals (explicitly out of scope for v1)

- Cancellation/voiding of purchase invoices; reversal of posted payable payments (correction = manual reversing JE).
- Product/item catalog or item FKs on lines (Feature 012 Inventory).
- Inventory/COGS accounting on purchase posting (single expense account in v1).
- Per-line account mapping or splitting across multiple expense/cost accounts.
- Currency handling (system is single-currency).
- Auto-sequenced invoice/payment numbers.
- Generalizing `SalesSettings` into a shared mapping table.
- Any new role or permission groups; any change to `apps/accounting` or `SalesSettings`.
- Early-payment (paying a draft invoice), prepayment, or credit notes.

## 5. Test Strategy Sketch

Mirror `apps/sales/tests/*` structure in `apps/purchases/tests/`:

1. **Vendors** (`test_vendors_api.py`): CRUD, idempotent code create, duplicate code 400, delete-with-invoices → deactivate, permissions matrix, tenant isolation (404/generic).
2. **Purchase invoices** (`test_purchase_invoices_api.py`): create (lines, totals, discount, tax), edit draft, posted immutability, number uniqueness, vendor ownership + inactive vendor, tenant isolation, due-date validation, permission matrix.
3. **Posting** (same file): success (one balanced JE with correct accounts), no-settings/config errors, Input-VAT-missing-when-tax>0 → 400, duplicate posting prevention (single JE), rollback (no partial state), cross-tenant account rejection, no disclosure.
4. **Payments** (`test_purchase_payments_api.py`): full/partial/multiple (20,000 → 7,000 → 13,000), outstanding consistency, overpayment at create and at post, Posted-invoice requirement, draft-edit/delete, posted immutability, idempotent post, tenant isolation (foreign invoice/account/payment), cross-direction guard (a Receivable payment cannot touch a purchase invoice and vice versa).
5. **Regression**: full `apps/` suite — baseline 153 must stay green.

## 6. Definition of Done

1. Single clean migration in `apps/purchases` (`0001_initial`) + a sales migration (`0003_payment_purchase_direction`) that resolves against it.
2. Purchase invoice posting creates exactly one balanced JE (`PUR-INV-{n}`): Dr Expense net, Dr Input VAT tax, Cr AP total; idempotent.
3. Payable payment posting creates Dr AP / Cr cash JE (`PAY-PUR-{inv}-{pay}`), row-locked, idempotent, overpayment-proof.
4. Full/partial/multiple AP examples pass; doing so never negative.
5. Cross-tenant vendor/invoice/account/payment access denied with generic errors; P0 tests green.
6. Feature 009/010 regression: all 153 existing tests pass untouched (API shape preserved).
7. Frontend: build passes; new files lint-clean (16 pre-existing only).
8. Spec artifacts complete and committed; AGENTS.md updated.