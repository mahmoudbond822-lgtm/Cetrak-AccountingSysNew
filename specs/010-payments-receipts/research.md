# Technical Research: Payments & Receipts

## Objective

Determine how to record customer payments against posted sales invoices with correct, tenant-isolated, idempotent accounting — reusing the existing Feature 009 architecture instead of inventing new infrastructure.

## 1. Existing Architecture Surveyed

### 1.1 Accounting core (`apps/accounting`)

| Artifact | Detail |
|---|---|
| `Account` | `TenantScopedModel`; `Type` = Asset/Liability/Equity/Revenue/Expense; `is_active`; parent hierarchy. Cash/bank accounts are `Asset` type. |
| `JournalEntry` | `TenantScopedModel`; `date`, `description`, `reference`, `posted`, `posted_at`; **unique `(tenant, reference)`** constraint; `total_debit`/`total_credit`/`is_balanced` properties. |
| `JournalEntryLine` | `account` (FK PROTECT), `debit`/`credit` `Decimal(19,4)` (never both set, never negative). |
| JournalEntryService / LedgerService / ReportService | All query through `.for_tenant()` + `entry__tenant_id` filters. Ledger running balance = `debit - credit`. |

**Implication**: A payment posting is a pure extension of the invoice-posting recipe — create a `JournalEntry` with `posted=True` inside `transaction.atomic()`, two lines (Dr cash, Cr AR), unique reference. The `(tenant, reference)` unique constraint doubles as the idempotency backstop.

### 1.2 Sales domain (`apps/sales`, Feature 009)

| Artifact | Detail |
|---|---|
| `SalesInvoice` | `TenantScopedModel`; `number` unique per tenant; `status` Draft→Posted; `total` `Decimal(19,4)`; `posted_journal` OneToOne; `posted_at`. |
| `SalesSettings` | `accounts_receivable`, `sales_revenue`, `vat_payable` (FK to Account). **AR account is the Cr target for payments.** |
| `SalesInvoiceService.post_invoice` | Validates settings, AR/revenue tenant+active, builds `SALES-INV-{number}` reference, creates balanced JE, marks invoice Posted. Catches `IntegrityError` → duplicate reference. |
| `SalesSettingsService.update` | Type-guards each mapping (AR must be `Asset`). |
| Serializers / views | Tenant-scoped by constructor (`self.tenant_id = request.tenant_id`); permission classes: `CanViewSales`, `CanManageSales`, `CanPostSalesInvoice`, `CanConfigureSales`. |
| `TenantScopedAccountField` | DRF field validating account is tenant-scoped + active — reusable to validate `cash_account`. |

**Implication**: Payments belong in `apps/sales` (no new app, matches Feature 009 precedent "no schema changes outside apps/sales"). The posting service mirrors `post_invoice` closely.

### 1.3 Conventions that lock in the design

- Money = `Decimal(19,4)`; **`float` is prohibited in all money paths** (LedgerService floats only for read-side display; payment posting must be Decimal throughout).
- `transaction.atomic()` around every write that touches both payments and journal entries.
- Permission model: no new roles, reuse existing sales permissions.
- Tenant isolation: `.for_tenant(request.tenant_id)` for every read; cross-tenant references surface as generic "not found"/validation errors.

## 2. Design Decisions

### D1 — Where does `Payment` live?
`apps/sales` (`sales_payment` table). It references `SalesInvoice` and `SalesSettings` from the same app, and only FKs outward to `accounting.Account`/`JournalEntry`. Adding a payment to sales keeps the whole customer→invoice→payment lifecycle in one app and avoids settings/INSTALLED_APPS churn.

### D2 — Status lifecycle
`Status = Draft | Posted`, mirroring invoices:
- **Draft**: editable (number, date, amount, method, account, reference, notes) and deletable. No journal entry.
- **Posted**: immutable — edit/delete rejected. A `journal_entry` OneToOne is set at posting.

**Posted → reversal**: deferred (FR-018). Rationale: reversal adds a second posting operation, allocation semantics (partial reversals), and status complexity. The manual reversing Journal Entry path already exists and is the documented correction route. MVP stays lean.

### D3 — Outstanding balance and overpayment prevention
`outstanding = invoice.total − Σ POSTED payments`. Only posted payments reduce the receivable (drafts have no ledger effect).

Overpayment is rejected **twice**:
1. **Serializer/creation time** — friendly UX error before the object exists.
2. **Posting time, inside the lock** — the authoritative check. Posting runs inside `transaction.atomic()` and `select_for_update()` on the `SalesInvoice` row, so two concurrent postings cannot both consume the same remaining balance. The `(tenant, reference)` unique constraint is the final backstop (in case of re-entrancy bugs).

### D4 — Which accounts feed the Journal Entry?
- **Dr**: the payment's `cash_account` — any active, tenant-scoped `Asset` account selected per payment. Validated via the existing `TenantScopedAccountField`.
- **Cr**: the **configured** `accounts_receivable` account from `SalesSettings` (not a per-payment choice). This is critical: if a payment credited a different AR account than the invoice debited, the receivable would never net to zero and the trial balance/ledger would be wrong. This is why D4 leans on settings rather than a free-form account picker.

JE is balanced by construction: Dr `amount`, Cr `amount`.

Reference: `PAY-INV-{invoice.number}-{payment.number}` — unique per tenant (matches invoice reference convention `SALES-INV-{number}`).

### D5 — Payment numbering
**User-supplied, unique per tenant**, exactly like `SalesInvoice.number`. Rationale: zero new increment/sequence machinery, symmetric with invoices, fully covered by the existing unique-constraint + `IntegrityError` pattern. Auto-sequencing (`PAY-000001`) is a documented future enhancement.

### D6 — Does Sales Settings need new fields?
**No.** AR comes from the existing `accounts_receivable`. Only one entry point changes: `SalesInvoiceService`/views already enforce "settings configured" for posting; payment posting enforces the same for the AR account. Missing AR config → posting fails; drafts can still be created.

### D7 — Invoice serializer additive fields
`SalesInvoiceSerializer` gains read-only `paid_amount` and `outstanding_balance`. This is purely additive (existing tests assert on keys they care about, not exact shape equality) and gives the payment UI the balance it needs without a second round-trip. The computation is a single lazy aggregate over posted payments (`paid_amount`), `outstanding_balance = total - paid_amount` clamped at 0.

### D8 — Error surface (no info disclosure)
Cross-tenant invoice → `"Invoice not found."` (same wording as sale service). Cross-tenant/inactive/non-`Asset` cash account → `TenantScopedAccountField` validation error. Duplicate number → `"Payment number already exists."`. Duplicate JE reference → `"Journal entry reference already exists."`. Message wording must test for stable substrings.

## 3. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Concurrent overpayment postings | Row lock on invoice row (`select_for_update`) inside the posting transaction; unique JE reference as backstop; atomicity via `transaction.atomic()`. |
| AR mismatch between invoice and payment (different accounts) | Payment **always** credits the settings-`accounts_receivable` account; verified tenant+active+Asset at posting. |
| Double booking via duplicate post requests | Posting guard (`status != Draft` → error) + reference uniqueness + idempotent test suite. |
| Float drift | Decimal throughout the posting path; no float coercion in payment total/balance logic (ledger read path already uses Decimal-string display). |
| Blowing up existing sales serializer tests with new fields | Additive read-only fields only; re-run full backend suite. |
| Schema churn in accounting app | No accounting schema changes; single new table + indexes in `apps/sales` migration `0002`. |
| UI over-engineering | Reuse 009 page/form patterns; only list, create, edit, post; confirm dialog for posting; backend validation is authoritative. |

## 4. Non-Goals (explicitly out of scope for v1)

- Reversal/cancellation of posted payments (FR-018) — manual JE is the correction path.
- Multi-invoice allocation on a single payment.
- Split payment across multiple cash accounts.
- Free-form payment methods beyond the fixed enum.
- Auto-generated sequential payment numbers.
- Early-collection / prepayment against non-posted invoices.
- Payment matching, bank feeds, deposit sl8/clearing, or statements.
- Any new permission/role.
- Currency handling (system is single-currency).

## 5. Test Strategy Sketch

Mirror `apps/sales/tests/test_sales_api.py` from Feature 009:

1. **Happy path**: create invoice → post invoice → create payment draft → post payment → assert one balanced JE, invoice `outstanding_balance == 0`, `paid_amount == total`.
2. **Partial/multiple**: 10,000 invoice; pay 4,000 (outstanding 6,000 acknowledged in both payment and invoice payloads); pay 6,000 (outstanding 0); third payment rejected.
3. **Overpayment**: create and post 10,001 against a 10,000 invoice → 400 with stable message, no JE.
4. **Status guards**: draft payment editable/deletable; posted immutable; posting a draft invoice's payment or an already-posted payment rejected.
5. **Tenant isolation**: payment/invoice/account from another tenant → rejected with generic error, no data leak (auth as tenant B, target tenant A objects).
6. **Account validation**: inactive account, non-Asset account, foreign-tenant account → validation error.
7. **Settings validation**: missing/inactive AR account → posting fails, draft create still OK.
8. **Number uniqueness**: duplicate number → 400.
9. **Idempotency**: repost → 400, single JE remains.
10. **Regression**: full suite (130 baseline expected + new).