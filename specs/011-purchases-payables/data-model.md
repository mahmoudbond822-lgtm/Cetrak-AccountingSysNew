# Data Model: Purchases & Accounts Payable (Feature 011)

## 1. New App: `apps/purchases`

All four tables live in a new `apps/purchases` app (already scaffolded in `INSTALLED_APPS`). Migration `apps/purchases/migrations/0001_initial.py`. No changes to `apps/accounting`; `apps/sales` gains one additive migration (`0003`).

### 1.1 `purchase_vendor`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK core.Tenant | Tenant isolation; set from `request.tenant_id`. |
| `id`, `created_at`, `updated_at` (inherited) | UUID / DateTime | BaseModel. |
| `code` | Char(50) | **Required**, stripped. Unique per tenant. |
| `name` | Char(255) | **Required**, stripped. |
| `email` | EmailField | null/blank. |
| `phone` | Char(50) | null/blank. |
| `address` | Text | null/blank. |
| `tax_id` | Char(50) | null/blank (VAT/TAX registration no.). |
| `is_active` | Boolean | default True; delete-with-invoices → deactivate. |

Constraints/indexes:

```python
constraints = [UniqueConstraint(fields=["tenant", "code"], name="unique_vendor_code_per_tenant")]
indexes = [Index(fields=["tenant"]), Index(fields=["is_active"])]
```

### 1.2 `purchase_invoice`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Tenant isolation. |
| `number` | Char(50) | **Required**, unique per tenant. |
| `vendor` | FK → `purchase_vendor` (PROTECT, `related_name="invoices"`) | **Required**; must be tenant-scoped + `is_active`. |
| `invoice_date` | DateField | Required. |
| `due_date` | DateField | null/blank; ≥ invoice_date. |
| `status` | Char(20), default `Draft` | `Draft` → `Posted`. |
| `notes` | Text | null/blank. |
| `discount` | DecimalField(19,4) | default 0; 0 ≤ discount ≤ subtotal. |
| `subtotal` | DecimalField(19,4) | computed. |
| `tax` | DecimalField(19,4) | computed (VAT). |
| `total` | DecimalField(19,4) | computed; > 0. |
| `posted_at` | DateTimeField | null; set at posting. |
| `posted_journal` | OneToOne → `accounting.JournalEntry` (PROTECT, `related_name="purchase_invoice"`), null/blank | Set at posting; blocks double posting. |

Constraints/indexes:

```python
constraints = [UniqueConstraint(fields=["tenant", "number"], name="unique_purchase_invoice_number_per_tenant")]
indexes = [Index(fields=["tenant", "status"]), Index(fields=["vendor"]), Index(fields=["tenant", "vendor", "invoice_date"])]
ordering = ["-created_at"]
```

### 1.3 `purchase_invoiceline`

| Field | Type | Rules |
|---|---|---|
| `id`, `created_at`, `updated_at` (inherited) | BaseModel | — |
| `invoice` | FK → `purchase_invoice` (CASCADE, `related_name="lines"`) | — |
| `description` | Char(255) | **Required** (free text; item FK arrives with Feature 012). |
| `quantity` | DecimalField(19,4) | **> 0**. |
| `unit_price` | DecimalField(19,4) | **≥ 0**. |
| `tax_rate` | DecimalField(5,2) | default 0; 0 ≤ rate ≤ 100. |
| `subtotal` / `tax` / `total` | DecimalField(19,4) | computed: `qty × price`, `subtotal × rate/100`, `subtotal + tax`. |

### 1.4 `purchase_settings`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Unique per tenant. |
| `accounts_payable` | FK → `accounting.Account` (PROTECT, `related_name="+"`), null/blank | **Liability**. Used on invoice posting (Cr) and payment posting (Dr). |
| `expense_account` | FK → `accounting.Account` (PROTECT, `related_name="+"`), null/blank | **Expense**. Dr on invoice posting (net). |
| `input_vat` | FK → `accounting.Account` (PROTECT, `related_name="+"`), null/blank | **Asset** (recoverable input VAT). Dr on invoice posting when `tax > 0`; required then. |

```python
constraints = [UniqueConstraint(fields=["tenant"], name="unique_purchase_settings_per_tenant")]
```

## 2. Generalized `Payment` (modifies existing `sales_payment`, `apps/sales`)

Feature 010's `Payment` is generalized to serve both receipts (Receivable) and vendor payments (Payable). Migration `apps/sales/migrations/0003_payment_purchase_direction.py`.

| Change | Detail |
|---|---|
| `direction` | Char(20), choices `Receivable`/`Payable`, **default `Receivable`** — existing rows unaffected, sales API unchanged. |
| `invoice` (sales, FK PROTECT, `related_name="payments"`) | becomes `null=True` — set when `direction=Receivable`. |
| `purchase_invoice` (new) | FK → `"purchases.PurchaseInvoice"` (PROTECT, `related_name="payments"`), `null=True` — set when `direction=Payable`. Lazy string reference (no import). |
| Check constraint | `check_payment_invoice_reference`: `(invoice IS NOT NULL AND purchase_invoice IS NULL) OR (invoice IS NULL AND purchase_invoice IS NOT NULL)` — a payment can never sit on both sides. |
| Index | added on `purchase_invoice`. |

Existing unique `(tenant, number)` and `(tenant, status)`/`invoice` indexes unchanged.

## 3. Relationships (ER summary)

```
Tenant 1───* Vendor *───1 PurchaseInvoice (1───* PurchaseInvoiceLine)
PurchaseInvoice 1───0..* Payment (purchase_invoice, direction=Payable)
SalesInvoice     1───0..* Payment (invoice,        direction=Receivable)
Payment *───1 Account (cash_account, Asset)          [shared with Feature 010]
PurchaseSettings 1───0..1 Account (accounts_payable / expense_account / input_vat)
```

## 4. Derived Value: outstanding AP (never stored)

```
paid_amount(purchase_invoice)  = Σ amount of Payment where purchase_invoice = doc
                                 and direction = Payable and status = POSTED
outstanding(purchase_invoice)  = max(total − paid_amount, 0)

new_payment_valid              ⟺ amount ≤ outstanding(purchase_invoice)
```

Computed with a single aggregate query; recomputed inside the posting transaction under `select_for_update` on the purchase invoice row.

## 5. Journal Entries produced

### 5.1 Purchase invoice posting (`PUR-INV-{number}`)

| Line | Account (source) | Debit | Credit |
|---|---|---|---|
| 1 | `expense_account` (settings) | `subtotal − discount` | — |
| 2 | `input_vat` (settings, only if tax > 0) | `tax` | — |
| 3 | `accounts_payable` (settings) | — | `total` |

Balanced by construction (Dr net + Dr tax = Cr total). `date = invoice_date`, `posted=True`.

### 5.2 Payable payment posting (`PAY-PUR-{invoice.number}-{payment.number}`)

| Line | Account (source) | Debit | Credit |
|---|---|---|---|
| 1 | `accounts_payable` (settings) | `amount` | — |
| 2 | `cash_account` (payment) | — | `amount` |

> **Accounting note**: paying a vendor **reduces** the AP liability (debit) and **reduces** cash (credit). This corrects the payment entry direction shown in the feature brief (Dr Cash / Cr AP), which would double-count both; documented as a deviation.

## 6. Why these choices

- **`purchase_settings` mirrors `sales_settings`**: same single-row-per-tenant pattern, same type-guarded service; generalizing SalesSettings was evaluated and rejected (D2) — different account sets, zero-risk additive.
- **Generalized `Payment` instead of a second payment table**: the lifecycle (draft→posted, outstanding, row-lock, idempotency) is identical; one model + one service with a `direction` dispatch avoids duplicating ~200 lines and keeps a single `(tenant, number)` space per tenant.
- **Check constraint for exactly-one invoice reference**: DB-level integrity that a payment can never be simultaneously a receipt and an expense — belt-and-braces to the service-level direction dispatch.
- **No `Cancelled`/`Void` status**: deferred (FR-018), consistent with sales; only Posted documents accept payments.
- **Input VAT as Asset**: recoverable VAT is a receivable-like asset; enforced and documented.

## 7. Migrations

1. `apps/purchases/migrations/0001_initial.py` — creates `purchase_vendor`, `purchase_invoice`, `purchase_invoiceline`, `purchase_settings` (+ constraints/indexes).
2. `apps/sales/migrations/0003_payment_purchase_direction.py` — adds `direction`, `purchase_invoice`, alters `invoice` to null, adds check constraint + index. Depends on `0001` (FK to purchase invoice) and on `purchases 0001`.

No data migrations. Reverse operations are symmetric drops/alters.