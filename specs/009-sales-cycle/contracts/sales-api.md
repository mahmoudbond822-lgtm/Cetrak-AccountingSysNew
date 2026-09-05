# API Contracts: Sales Cycle (Foundation)

Base path: `/api/v1/sales/`. All endpoints require a valid bearer JWT and a tenant context (`X-Tenant-ID` header or JWT `tenant_id` claim); the existing `TenantResolutionMiddleware` enforces membership (403). Money is JSON strings using up to 4 decimal places. Errors follow the DRF convention `{"detail": "<message>"}` or field-keyed objects.

## Customers

### `GET /sales/customers/`

List customers for the active tenant.

- Query params: `?active=true|false` (default: active customers only)
- Permissions: `CanViewSales` (Admin, Accountant, Manager)
- Response 200: array of customer objects (fields below).

### `POST /sales/customers/`

Create a customer. Permissions: `CanManageSales`.

Request body:

```json
{
  "code": "C-001",
  "name": "Acme Trading",
  "email": "billing@acme.example",
  "phone": "+1 555 0100",
  "address": "1 Main Street, Springfield",
  "tax_id": "123456789",
  "is_active": true
}
```

- 201: created customer | 400: validation (duplicate code, missing name/code, cross-tenant reference) | 403: forbidden.

### `GET /sales/customers/{id}/`

Retrieve one customer. 404-equivalent for ids outside the tenant (no disclosure).

### `PATCH /sales/customers/{id}/`

Update name/contact/address/status. Permissions: `CanManageSales`. 200 on success; 404 outside tenant; 403 forbidden.

### Customer response shape

```json
{
  "id": "uuid",
  "code": "C-001",
  "name": "Acme Trading",
  "email": "billing@acme.example",
  "phone": "+1 555 0100",
  "address": "1 Main Street, Springfield",
  "tax_id": "123456789",
  "is_active": true,
  "created_at": "2026-09-05T10:00:00Z",
  "updated_at": "2026-09-05T10:00:00Z"
}
```

## Sales Settings (accounting mapping)

### `GET /sales/settings/`

Return the active tenant's sales accounting mapping. Permissions: `CanConfigureSales` (Admin only).

```json
{
  "accounts_receivable": "uuid",
  "sales_revenue": "uuid",
  "vat_payable": "uuid",
  "accounts_receivable_name": "Accounts Receivable",
  "sales_revenue_name": "Sales Revenue",
  "vat_payable_name": "VAT Payable"
}
```

Nulls are allowed when accounts are not yet selected.

### `PUT /sales/settings/`

Replace the mapping. Permissions: `CanConfigureSales`.

Request body: `{"accounts_receivable": "uuid", "sales_revenue": "uuid", "vat_payable": "uuid"}` (all may be null/omitted).

- 200: saved mapping | 400: account from another tenant, wrong account type, or malformed UUID (no disclosure) | 403: forbidden.

## Sales Invoices

### `GET /sales/invoices/`

List invoices for the active tenant (newest first).

- Query params: `?status=Draft|Posted`
- Permissions: `CanViewSales`

### `POST /sales/invoices/`

Create a draft invoice. Permissions: `CanManageSales`.

Request body:

```json
{
  "number": "INV-2026-001",
  "customer_id": "uuid",
  "invoice_date": "2026-09-05",
  "due_date": "2026-10-05",
  "discount": "0.00",
  "notes": "September order",
  "lines": [
    {
      "description": "Product A",
      "quantity": "2",
      "unit_price": "100.00",
      "tax_rate": "15.00"
    }
  ]
}
```

- 201: draft invoice with computed totals | 400: validation (duplicate number, no lines, zero/negative quantity, negative price, tax rate outside 0–100, missing line description, discount ≥ subtotal, zero/negative total, due_date before invoice_date, cross-tenant customer) | 403: forbidden.

### Invoice response shape

```json
{
  "id": "uuid",
  "number": "INV-2026-001",
  "customer_id": "uuid",
  "customer_name": "Acme Trading",
  "invoice_date": "2026-09-05",
  "due_date": "2026-10-05",
  "status": "Draft",
  "discount": "0.00",
  "subtotal": "200.00",
  "tax": "30.00",
  "total": "230.00",
  "notes": "September order",
  "posted_at": null,
  "lines": [
    {
      "id": "uuid",
      "description": "Product A",
      "quantity": "2.0000",
      "unit_price": "100.0000",
      "tax_rate": "15.00",
      "subtotal": "200.0000",
      "tax": "30.0000",
      "total": "230.0000"
    }
  ]
}
```

### `GET /sales/invoices/{id}/`

Retrieve one invoice with lines. 404-equivalent outside tenant.

### `PATCH /sales/invoices/{id}/`

Edit a **Draft** invoice only (lines are replaced as a whole). Permissions: `CanManageSales`.

- 200: updated draft | 400: validation | 403: forbidden | 405: posted invoices are immutable | 404: outside tenant.

### `POST /sales/invoices/{id}/post/`

Finalize a draft invoice and create the balanced accounting entry. Permissions: `CanPostSalesInvoice` (Admin, Accountant).

- 200: posted invoice (status="Posted", `posted_at` set):

```json
{
  "id": "uuid",
  "number": "INV-2026-001",
  "status": "Posted",
  "posted_at": "2026-09-05T11:00:00Z",
  "journal_entry_id": "uuid"
}
```

- 400: already posted; incomplete/empty account mapping; invalid or inactive mapped account; journal reference collision (all with generic, non-disclosing messages) | 403: forbidden | 404: outside tenant.

On failure, the invoice remains `Draft`, no journal entry is created, and no balances change (single transaction).

## Accounting Entry Produced by Posting

Dr `accounts_receivable` = invoice `total`
Cr `sales_revenue` = invoice `subtotal` − invoice `discount`
Cr `vat_payable` = invoice `tax` (omitted when tax = 0)

`reference = "SALES-INV-{number}"`, `date = invoice_date`, entry is created already posted.