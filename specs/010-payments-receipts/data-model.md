# Data Model: Payments & Receipts (Feature 010)

## 1. New Table: `sales_payment`

Stored in the existing `apps/sales` app (migration `0002_...`). No changes to `accounting` tables.

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK → tenants.Tenant | Tenant isolation; set from `request.tenant_id`. |
| `id` (inherited) | UUID (BaseModel) | — |
| `created_at` / `updated_at` (inherited) | DateTime | — |
| `number` | Char(50) | **Required**, user-supplied. Unique per tenant. |
| `invoice` | FK → `SalesInvoice` (PROTECT) | **Required**. Must be tenant-scoped and **Posted**. |
| `payment_date` | DateField | **Required**. |
| `amount` | DecimalField(19,4) | **Required**, > 0, ≤ outstanding balance at create and post. |
| `method` | Char(20) | Choices: `Cash`, `Bank Transfer`, `Card`, `Check`. |
| `cash_account` | FK → `accounting.Account` (PROTECT, `related_name="+"`) | **Required**. Tenant-scoped, `is_active=True`, type `Asset`. |
| `reference` | Char(255), null/blank | External payment reference (bank ref / check no.), informational. |
| `notes` | Text, null/blank | Informational. |
| `status` | Char(20), default `Draft` | `Draft` → `Posted`. |
| `journal_entry` | OneToOne → `accounting.JournalEntry` (PROTECT, `related_name="payment"`), null/blank | Set at posting; ensures 1:1 payment↔JE and blocks double posting. |
| `posted_at` | DateTime, null/blank | Set at posting. |

### Constraints & Indexes

```python
constraints = [
    models.UniqueConstraint(
        fields=["tenant", "number"],
        name="unique_payment_number_per_tenant",
    ),
]
indexes = [
    models.Index(fields=["tenant", "status"]),
    models.Index(fields=["invoice"]),
]
```

`on_delete` choices:
- `invoice` → **PROTECT** (a payment must not silently orphan when an invoice is deleted; invoices themselves are PROTECTed down the line and posted invoices are immutable anyway).
- `cash_account` → **PROTECT** (matches `JournalEntryLine.account`).
- `journal_entry` → **PROTECT** (a posted JE must never disappear after being linked).

## 2. Relationships (ER summary)

```
Tenant 1───* Payment *───1 SalesInvoice
Payment *───1 Account (cash_account, Asset)
Payment 1───0..1 JournalEntry (one-to-one, set on posting)
SalesInvoice 1───0..* Payment
SalesSettings 1───0..1 Account (accounts_receivable) ← Cr target on posting
```

- `SalesInvoice` gains no columns; `fine_balance` is **derived**, never stored.
- `SalesSettings` unchanged (AR account reused).
- `JournalEntry` / `JournalEntryLine` unchanged.

## 3. Derived Value: outstanding balance (never stored)

```
paid_amount(invoice)      = Σ amount of Payment where invoice=invoice
                            and status=POSTED and tenant=tenant
outstanding_balance(inv)  = max(invoice.total − paid_amount(invoice), 0)

new_payment_valid         ⟺ amount ≤ outstanding_balance(invoice)
```

Computed via a single aggregate query over posted payments; recomputed inside the posting transaction while the invoice row is locked (see Research §D3).

## 4. Journal Entry produced on posting

| Line | Account (source) | Debit | Credit |
|---|---|---|---|
| 1 | `cash_account` (payment) | `amount` | — |
| 2 | `SalesSettings.accounts_receivable` | — | `amount` |

- `JournalEntry.date = payment.payment_date`
- `JournalEntry.description = "Payment {number} for invoice {invoice.number}"`
- `JournalEntry.reference = "PAY-INV-{invoice.number}-{payment.number}"` (unique per tenant)
- `posted=True`, `posted_at = now`
- Balanced by construction (`Dr amount = Cr amount`), exactly two lines.

## 5. Why these choices

- **Single Dr (cash_account) + Cr (settings AR)**: guarantees the receivable net-tracks the invoice posting. Selecting a different AR per payment would corrupt the AR ledger (see Research §D4).
- **Draft→Posted status**: mirrors Feature 009 invoices; drafts are cheap, reversible, and offline-ready; posting is the single ledger-committing moment.
- **`journal_entry` OneToOne PROTECT**: structural idempotency — a payment can never host a second entry and a linked entry can never be deleted.
- **No reversal field**: deliberately absent in v1 (FR-018). Correction = manual reversing JE. A future `reversed` state would reuse the same one-to-one pattern plus a reversing entry with reference `REV-{payment_number}`.
- **Numbering user-supplied + unique**: identical to invoices; no sequence machinery; `IntegrityError` → friendly duplicate error. Auto-sequencing postponed.

## 6. Migration

Single migration `apps/sales/migrations/0002_payment.py`:
- `CreateModel(Payment)` with the fields, constraints, indexes above.
- No data migration (new feature, no backfill).
- Reverse: `DropModel`.