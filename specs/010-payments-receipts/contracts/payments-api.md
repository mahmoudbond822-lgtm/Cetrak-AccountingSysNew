# API Contracts: Payments & Receipts (Feature 010)

Base path: `/api/v1/sales`. All endpoints require authentication and tenant scoping via the standard middleware; **all lookups are tenant-scoped** (foreign-tenant objects render as not-found/validation errors).

Common headers: `Authorization: Bearer <token>` (existing auth). Request/response bodies are JSON. Money values are decimal strings.

## 1. `POST /api/v1/sales/payments/` — Create a draft payment

### Request body

```json
{
  "number": "PAY-0001",
  "invoice": "5f9e2f7a-...",
  "payment_date": "2026-09-05",
  "amount": "4000.0000",
  "method": "Bank Transfer",
  "cash_account": "ca63fe2b-...",
  "reference": "TRF-88213",
  "notes": "First instalment"
}
```

### Validation rules (create-time UX checks)

| Field | Rule |
|---|---|
| `number` | Required; unique per tenant → else `400 {"number": "Payment number already exists."}` |
| `invoice` | Required; must exist in tenant and be **Posted** → else `400 {"invoice": "Only posted invoices can receive payments."}` / `"Invoice not found."` |
| `payment_date` | Required, valid ISO date |
| `amount` | Required; Decimal; > 0; ≤ invoice outstanding balance → else `400 {"amount": "Amount exceeds the outstanding balance."}` |
| `method` | Required; one of `Cash`, `Bank Transfer`, `Card`, `Check` |
| `cash_account` | Required via `TenantScopedAccountField`: tenant-scoped, active, type `Asset` → else validation error |
| `reference`, `notes` | Optional |

### Response: `201 Created`

```json
{
  "id": "e6b2a922-...",
  "number": "PAY-0001",
  "invoice": {
    "id": "5f9e2f7a-...",
    "number": "INV-1000",
    "customer": {"id": "...", "code": "C-001", "name": "Acme Corp"},
    "total": "10000.0000",
    "paid_amount": "0.0000",
    "outstanding_balance": "10000.0000"
  },
  "payment_date": "2026-09-05",
  "amount": "4000.0000",
  "method": "Bank Transfer",
  "cash_account": "ca63fe2b-...",
  "reference": "TRF-88213",
  "notes": "First instalment",
  "status": "Draft",
  "journal_entry": null,
  "posted_at": null,
  "created_at": "2026-09-05T10:00:00Z",
  "updated_at": "2026-09-05T10:00:00Z"
}
```

## 2. `GET /api/v1/sales/payments/` — List payments

Query params (all optional): `status` (`Draft`/`Posted`), `invoice` (invoice UUID).

Response: `200` — array of payment objects (same shape as create response), newest first.

## 3. `GET /api/v1/sales/payments/{id}/` — Retrieve

Response: `200` — payment object. `404` if not in tenant.

## 4. `PATCH /api/v1/sales/payments/{id}/` — Update a draft

| Rule | Behavior |
|---|---|
| Only `Draft` payments are editable | Posted → `400 {"detail": "Only draft payments can be edited."}` |
| Same field validation as create | Surfaces the same messages |
| `invoice` change | Allowed on drafts (posting re-validates against the new invoice) |

Response: `200` — updated payment object.

## 5. `DELETE /api/v1/sales/payments/{id}/` — Delete a draft

| Rule | Behavior |
|---|---|
| Only `Draft` payments are deletable | Posted → `400 {"detail": "Only draft payments can be deleted."}` |
| Deleting a draft never creates/touches journal entries | — |

Response: `204 No Content`.

## 6. `POST /api/v1/sales/payments/{id}/post_payment/` — Post a draft payment

Commits the ledger effect atomically: creates the Journal Entry, links it, marks the payment `Posted`.

### Behavior & errors

| Condition | Result |
|---|---|
| Success | `200` — payment object with `status: "Posted"`, `journal_entry: {id}`, `posted_at` set; invoice `outstanding_balance` reduced |
| Payment not found (or other tenant) | `404 {"detail": "Payment not found."}` |
| Already posted (idempotency) | `400 {"detail": "Payment is already posted."}` — no second JE |
| Invoice not posted | `400 {"detail": "Invoice is not posted."}` |
| Overpayment (incl. concurrent race) | `400 {"detail": "Amount exceeds the outstanding balance."}` — transaction rolls back |
| Missing/inactive/foreign AR configuration | `400 {"detail": "Sales accounting settings are not configured."}` |
| Duplicate JE reference | `400 {"detail": "Journal entry reference already exists."}` |

Response `200` body = payment object (shape as §1 response, with posting fields populated).

## 7. Additive invoice fields (existing API, backward-compatible)

`GET /api/v1/sales/invoices/` and `/invoices/{id}/` now include two extra read-only keys per invoice:

```json
"paid_amount": "4000.0000",
"outstanding_balance": "6000.0000"
```

These are computed from posted payments and are always returned; no existing field changes.

## 8. Frontend wiring (P3)

| Concern | Backing API |
|---|---|
| Payments list | `GET /api/v1/sales/payments/?status=Posted` (+ `?status=Draft`) |
| Posted invoices to receive payments | `GET /api/v1/sales/invoices/?status=Posted` (now with `outstanding_balance`) |
| Cash/bank account picker | existing `GET /api/v1/accounting/accounts/?type=Asset&is_active=true` |
| Create draft | `POST /api/v1/sales/payments/` |
| Edit/delete draft | `PATCH` / `DELETE /api/v1/sales/payments/{id}/` |
| Post (confirm dialog) | `POST /api/v1/sales/payments/{id}/post_payment/` |

## 9. Permission map

| Action | Permission |
|---|---|
| List/retrieve payments | `CanViewSales` |
| Create/edit/delete draft payments | `CanManageSales` |
| Post a payment | `CanPostSalesInvoice` (reused) |

All inherit tenant scoping from the sales views; no new permissions.