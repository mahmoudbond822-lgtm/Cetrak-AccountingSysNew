# API Contracts: Payments (Feature 011 — generalized Payment)

The `Payment` model/service from Feature 010 is generalized with a `direction` field (`Receivable | Payable`). Two clean API surfaces expose it:

- **Sales receipts** (`/api/v1/sales/payments/`) — **unchanged** (Feature 010 contract remains valid, default `direction=Receivable`).
- **Purchase payments** (`/api/v1/purchases/payments/`) — new (this document).

Contract for the shared service mechanics (idempotency, row-lock, tenant isolation) is preserved from Feature 010.

## Permission model (purchases payments)

| Capability | List/View | Create pipe | Edit/Delete draft | Post payment |
|---|---|---|---|---|
| `CanViewPurchases` | ✓ | — | — | — |
| `CanManagePurchases` | ✓ | ✓ | ✓ | — |
| `CanPostPurchaseInvoice` | ✓ | ✓ | ✓ | ✓ |

(Parallel to Feature 010, where the sales posting permission `CanPostSalesInvoice` covers payment posting.)

## Purchase payments

### `GET /api/v1/purchases/payments/`
Only `direction=Payable` payments for the tenant. Filters: `?status=` (Draft/Posted), `?purchase_invoice=` (invoice id). Item:

```json
{
  "id": "uuid", "number": "PAY-002", "direction": "Payable",
  "purchase_invoice_id": "uuid",
  "purchase_invoice": {"id": "uuid", "number": "PUR-2026-001",
                       "vendor": {"id": "uuid", "code": "V001", "name": "Alpha Supplies Ltd"},
                       "total": "20000.0000", "paid_amount": "17000.0000", "outstanding_balance": "3000.0000"},
  "vendor_name": "Alpha Supplies Ltd",
  "payment_date": "2026-09-05", "amount": "7000.0000", "method": "Cash",
  "cash_account": "uuid", "cash_account_name": "Bank Account",
  "reference": null, "notes": null, "status": "Posted",
  "journal_entry_id": "uuid|null", "posted_at": "…",
  "created_at": "…", "updated_at": "…"
}
```

### `POST /api/v1/purchases/payments/`
Body: `{number, purchase_invoice_id, cash_account, payment_date, amount?, method, reference?, notes?}`. The service computes `amount` as the invoice's outstanding balance when omitted.

- `201` DTO `status="Draft"`, `direction="Payable"`.
- `400`:
  - `{"number": ["Payment number already exists."]}`
  - `{"purchase_invoice_id": ["Invalid pk \"…\" — object does not exist."]}` — foreign/unknown, or (belt-and-braces) a Receivable-target/draft invoice (serializer resolves posted invoices only).
  - `{"cash_account": ["Invalid pk …"]}` — foreign/unknown asset account.
  - `{"amount": ["Amount must be greater than zero."]}`
  - `{"amount": ["Amount exceeds the outstanding balance."]}` (0 < amount > outstanding; outstanding = total − Σ posted Payable) — "0" with 0 outstanding is also rejected.

### `GET /api/v1/purchases/payments/{id}/`
`200` DTO | `404` `{"detail": "Payment not found."}` (foreign/unknown).

### `PATCH /api/v1/purchases/payments/{id}/`
Draft only. `200` | `400` | `400` (Posted) `{"detail": "Only draft payments can be edited."}` | `404`.

### `DELETE /api/v1/purchases/payments/{id}/`
Draft only → `204`; Posted → `400` `{"detail": "Only draft payments can be deleted."}`; foreign → `404`.

### `POST /api/v1/purchases/payments/{id}/post_payment/`
Requires `CanPostPurchaseInvoice`. No body. Atomically posts:
- `200` DTO with `status="Posted"`, `journal_entry_id`; one Journal Entry `PAY-PUR-{invoice.number}-{payment.number}` — **Dr Accounts Payable (settings, Liability), Cr cash_account (payment, Asset)**, each `amount`.
- `400` `{"detail": "Only draft payments can be posted."}` (already posted).
- `400` `{"detail": "Amount exceeds the outstanding balance."}` — row-locked re-check (`select_for_update` on the purchase invoice) defeats concurrent overpayment.
- `400` `{"detail": "Purchase accounting settings are not configured."}` / `{"detail": "Purchase accounting settings are invalid."}`.
- `400` `{"detail": "Journal entry reference already exists."}` (idempotency backstop).

## Cross-direction integrity

- A `Receivable` payment can only reference a **sales** invoice; a `Payable` payment can only reference a **purchase** invoice — enforced by serializer resolution, service dispatch, and a DB check constraint (exactly one invoice reference per payment).
- Sales endpoints never expose `purchase_invoice`; purchases endpoints never expose `invoice`.
- `PaymentService` signatures default to `direction="Receivable"` so the Feature 010 sales surface is source- and behavior-compatible with zero call-site changes.