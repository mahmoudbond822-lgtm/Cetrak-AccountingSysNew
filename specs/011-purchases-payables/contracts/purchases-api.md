# API Contracts: Purchases (Feature 011)

All endpoints are under the versioned prefix `/api/v1/purchases/`, JWT-authenticated, tenant-scoped. Errors use DRF structured errors (`{"detail": "..."}` / field errors). Access uses the purchases permission classes (sales roles: `Admin`, `Accountant`, `Manager`).

## Permission model

| Capability | View | List | Create | Update/Delete | Post invoice | Configure settings |
|---|---|---|---|---|---|---|
| `CanViewPurchases` (role: Admin, Accountant, Manager) | ✓ | ✓ | — | — | — | — |
| `CanManagePurchases` (role: Admin, Accountant) | ✓ | ✓ | ✓ | ✓ (drafts) | — | — |
| `CanPostPurchaseInvoice` (role: Admin, Accountant) | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `CanConfigurePurchases` (role: Admin) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## Vendors

### `GET /api/v1/purchases/vendors/`
List active vendors for the tenant. Supports `?search=`, `?is_active=`. Response (paginated if enabled):

```json
[{
  "id": "uuid", "code": "V001", "name": "Alpha Supplies Ltd", "email": "ap@alpha.example",
  "phone": "+44 20 7946 0001", "address": "1 Foundry Lane", "tax_id": "GB 123 4567 89",
  "is_active": true, "created_at": "…", "updated_at": "…"
}]
```

### `POST /api/v1/purchases/vendors/`
Body: `{code, name, email?, phone?, address?, tax_id?}`.
- `201` on success (echoes the DTO above).
- `400` on missing/blank `code`/`name`, or duplicate tenant code → `{"code": ["Vendor code already exists."]}`.
- `401` unauth, `403` unless `CanManagePurchases`.

### `GET /api/v1/purchases/vendors/{id}/`
- `200` the DTO; `404` `{"detail": "Vendor not found."}` for foreign/unknown id (no disclosure).

### `PATCH /api/v1/purchases/vendors/{id}/`
Partial update of `code`/`name`/contact fields (code uniqueness re-checked). `200` | `400` | `403` | `404`.

### `DELETE /api/v1/purchases/vendors/{id}/`
- `204` always when the vendor exists: **no-op hard delete** — vendors with purchase invoices are deactivated (`is_active=False`) instead; vendors without invoices are deactivated too (conservative; consistent with customers).
- `404` for foreign/unknown id. `403` unless `CanManagePurchases`.

## Purchase invoices

### `GET /api/v1/purchases/invoices/`
List for tenant. Filters: `?status=` (Draft/Posted), `?vendor_id=`. Each item:

```json
{
  "id": "uuid", "number": "PUR-2026-001",
  "vendor": {"id": "uuid", "code": "V001", "name": "Alpha Supplies Ltd"},
  "invoice_date": "2026-09-01", "due_date": "2026-10-01", "status": "Posted",
  "notes": null, "discount": "0.0000", "subtotal": "10000.0000", "tax": "1500.0000",
  "total": "11500.0000", "paid_amount": "11500.0000", "outstanding_balance": "0.0000",
  "posted_at": "…", "posted_journal": "uuid|null",
  "lines": [{"id": "uuid", "description": "Steel beams", "quantity": "10.0000",
             "unit_price": "1000.0000", "tax_rate": "15.00",
             "subtotal": "10000.0000", "tax": "1500.0000", "total": "11500.0000"}],
  "created_at": "…", "updated_at": "…"
}
```

### `POST /api/v1/purchases/invoices/`
Body: `{number, vendor_id, invoice_date, due_date?, notes?, discount?, lines:[{description, quantity, unit_price, tax_rate?}]}`.
- `201` DTO with `status="Draft"`, `paid_amount="0.0000"`.
- `400`: blank/duplicate `number` (`{"number": ["Invoice number already exists."]}`); missing `vendor_id`; foreign/inactive vendor (`{"vendor_id": ["Vendor not found."]}`); `tax_rate` outside 0–100; `quantity ≤ 0`; negative `unit_price`; `discount > subtotal`; `due_date < invoice_date`; zero/negative total.

### `GET /api/v1/purchases/invoices/{id}/`
`200` DTO | `404` `{"detail": "Invoice not found."}` (foreign/unknown).

### `PATCH /api/v1/purchases/invoices/{id}/`
Draft only; `lines` replace. `200` | `400` (as POST) | `403` (Posted) `{"detail": "Only draft purchase invoices can be edited."}` | `404`.

### `DELETE /api/v1/purchases/invoices/{id}/`
Draft only → `204`; Posted → `403` `{"detail": "Only draft purchase invoices can be deleted."}`; foreign → `404`.

### `POST /api/v1/purchases/invoices/{id}/post_invoice/`
Requires `CanPostPurchaseInvoice`. No body. Atomically posts:
- `200` DTO with `status="Posted"`, `posted_at`, `posted_journal`; one Journal Entry `PUR-INV-{number}` — Dr expense (net), Dr input VAT (`tax` > 0 only, **required** then), Cr accounts payable (`total`).
- `400` `{"detail": "Only draft purchase invoices can be posted."}` (already posted).
- `400` `{"detail": "Purchase accounting settings are not configured."}` (AP/Expense missing, or Input VAT missing while `tax > 0`).
- `400` `{"detail": "Invalid account type for purchase accounting settings."}` (wrong account types).
- `400` `{"detail": "Journal entry reference already exists."}` (race backstop; idempotent — never a second JE).

## Purchase settings

### `GET /api/v1/purchases/settings/current/`
Supports `OPTIONS` for account metadata (reuse pattern). Returns for `GET`:

```json
{
  "tenant_id": "uuid",
  "accounts_payable": {"id": "uuid", "code": "AP", "name": "Accounts Payable", "type": "Liability"},
  "expense_account": {"id": "uuid", "code": "6300", "name": "Purchases", "type": "Expense"},
  "input_vat": {"id": "uuid", "code": "1205", "name": "Input VAT", "type": "Asset"},
  "updated_at": "…"
}
```

`null` for unset accounts. `404` `{"detail": "Purchase accounting settings are not configured."}` if no row and account info is required (view exposes account-type metadata so the frontend can filter `AccountSelect`).

### `POST /api/v1/purchases/settings/current/`
Atomically create-or-update the single settings row (requires `CanConfigurePurchases`; Admin). Body accepts account ids:

```json
{"accounts_payable_id": "uuid", "expense_account_id": "uuid", "input_vat_id": "uuid"}
```

- `200` the DTO.
- `400` `{"accounts_payable_id": ["Account must be of type 'Liability'."]}` / `…'expense_account_id': ["Account must be of type 'Expense'."]` / `…'input_vat_id': ["Account must be of type 'Asset'."]`.
- `400` `{"accounts_payable_id": ["Account not found."]}` for foreign/unknown accounts (no disclosure); inactive account mirrors sales.
- `403` unless `CanConfigurePurchases`.

## Tenant isolation

Every resource resolves through `.for_tenant(request.tenant_id)`; a foreign tenant's vendor/invoice/account is indistinguishable from "not found" (`404`, generic detail only). No endpoint ever returns rows outside the requesting tenant.