# Data Model: Sales Cycle (Foundation)

All sales models are tenant-scoped and follow the existing `TenantScopedModel` / `BaseModel` conventions from `apps/core/models.py`. Money uses `DecimalField(max_digits=19, decimal_places=4)` matching the accounting module. Tables use the `sales_` prefix convention (`db_table`).

## Customer

Represents a party the workspace sells to. Every customer belongs to exactly one tenant.

**Fields**:

- `id`: UUID primary key (from `BaseModel`)
- `tenant`: FK to `core.Tenant` (from `TenantScopedModel`)
- `code`: `CharField(max_length=50)` — tenant-scoped unique customer code
- `name`: `CharField(max_length=255)`
- `email`: `EmailField(blank=True, null=True)`
- `phone`: `CharField(max_length=50, blank=True, null=True)`
- `address`: `TextField(blank=True, null=True)`
- `tax_id`: `CharField(max_length=50, blank=True, null=True)` — optional VAT/tax identifier
- `is_active`: `BooleanField(default=True)`
- `created_at` / `updated_at`: timestamps (from `BaseModel`)

**Relationships**:

- Belongs to exactly one tenant
- May be referenced by many sales invoices in the same tenant
- Referenced customers are protected from deletion (`PROTECT`) once invoices exist

**Constraints**:

- `UniqueConstraint(fields=["tenant", "code"], name="unique_customer_code_per_tenant")`
- Database index on `tenant`

**Validation Rules**:

- Customer codes are unique within a tenant; the same code is allowed across tenants
- Customers are never accessible across tenants (every query uses `for_tenant`)
- New invoices may only reference active customers

## Sales Invoice

Represents a sales document issued to a customer. Lifecycle: **Draft** → **Posted**. Posted invoices are immutable.

**Fields**:

- `id`: UUID primary key
- `tenant`: FK to `core.Tenant`
- `number`: `CharField(max_length=50)` — tenant-scoped unique invoice number
- `customer`: FK to `Customer`, `on_delete=PROTECT`
- `invoice_date`: `DateField`
- `due_date`: `DateField(blank=True, null=True)`
- `status`: `CharField(choices=("Draft", "Posted"), default="Draft")`
- `notes`: `TextField(blank=True, null=True)`
- `discount`: `DecimalField(max_digits=19, decimal_places=4, default=0)` — header-level discount applied to subtotal
- `subtotal`: `DecimalField(max_digits=19, decimal_places=4, default=0)` — Σ (quantity × unit_price)
- `tax`: `DecimalField(max_digits=19, decimal_places=4, default=0)` — Σ (line tax)
- `total`: `DecimalField(max_digits=19, decimal_places=4, default=0)` — subtotal − discount + tax
- `posted_at`: `DateTimeField(blank=True, null=True)`
- `posted_journal`: `OneToOneField("accounting.JournalEntry", null=True, blank=True, on_delete=PROTECT, related_name="sales_invoice")` — the exact journal entry created by posting; guarantees idempotency and links the documents
- `created_at` / `updated_at`

**Relationships**:

- Belongs to exactly one tenant
- Belongs to one customer in the same tenant
- Owns one or more `SalesInvoiceLine` records
- When posted, links to exactly one `JournalEntry` in the same tenant

**Constraints**:

- `UniqueConstraint(fields=["tenant", "number"], name="unique_invoice_number_per_tenant")`
- Database indexes on `tenant` and `customer`

**Validation Rules**:

- Invoice numbers are unique per tenant
- At least one valid line is required
- `discount` ≥ 0, `discount` ≤ `subtotal`, and `total` = subtotal − discount + tax must be > 0 (prevents zero-amount or negative invoices that could never produce a valid journal entry)
- `due_date` ≥ `invoice_date` when provided
- Only `Draft` invoices can be edited, deleted, or posted
- Posted invoices have exactly one linked journal entry and cannot be modified

## Sales Invoice Line

Represents one line item on a sales invoice.

**Fields**:

- `id`: UUID primary key
- `invoice`: FK to `SalesInvoice`, `on_delete=CASCADE`, `related_name="lines"`
- `description`: `CharField(max_length=255)` / text
- `quantity`: `DecimalField(max_digits=19, decimal_places=4)` — must be > 0
- `unit_price`: `DecimalField(max_digits=19, decimal_places=4)` — must be ≥ 0
- `tax_rate`: `DecimalField(max_digits=5, decimal_places=2, default=0)` — percentage (e.g., `15.00` = 15%)
- `subtotal`: `DecimalField(max_digits=19, decimal_places=4)` — quantity × unit_price
- `tax`: `DecimalField(max_digits=19, decimal_places=4)` — subtotal × tax_rate / 100
- `total`: `DecimalField(max_digits=19, decimal_places=4)` — subtotal + tax
- `created_at` / `updated_at`

**Relationships**:

- Belongs to exactly one sales invoice

**Validation Rules**:

- A non-empty description is required on every line
- `quantity` > 0
- `unit_price` ≥ 0
- `tax_rate` ≥ 0 and ≤ 100.00
- Line sums are computed in `Decimal` and stored for the audit trail
- Headers roll up line subtotal, tax, and total; header discount is applied once at header level

## Sales Accounting Settings

A per-tenant singleton configuration mapping invoice posting to the workspace's chart of accounts. Exists so the system never hard-codes account IDs.

**Fields**:

- `id`: UUID primary key
- `tenant`: FK to `core.Tenant` (unique per tenant)
- `accounts_receivable`: FK to `accounting.Account`, `on_delete=PROTECT`, nullable, must be type `Asset`
- `sales_revenue`: FK to `accounting.Account`, `on_delete=PROTECT`, nullable, must be type `Revenue`
- `vat_payable`: FK to `accounting.Account`, `on_delete=PROTECT`, nullable, must be type `Liability`
- `created_at` / `updated_at`

**Relationships**:

- Belongs to exactly one tenant
- References up to three accounts within the same tenant

**Constraints**:

- `UniqueConstraint(fields=["tenant"], name="unique_sales_settings_per_tenant")`

**Validation Rules**:

- Referenced accounts must belong to the same tenant as the settings
- Account types are validated against the required category
- Accounts must be active at posting time
- A "complete" mapping has all three accounts set; posting requires a complete mapping

## Accounting Journal Entry (existing, reused)

When an invoice is posted, the following balanced journal entry is created in the workspace's ledger:

- Line 1: **Dr** `accounts_receivable` = invoice `total`
- Line 2: **Cr** `sales_revenue` = invoice `subtotal` − invoice `discount`
- Line 3: **Cr** `vat_payable` = invoice `tax` (only when `tax` > 0)

Balanced by construction: `total = (subtotal − discount) + tax`. The entry uses:

- `date` = invoice `invoice_date`
- `reference` = `SALES-INV-{number}` (unique per tenant because invoice numbers are)
- `description` = invoice summary text
- `posted = True`, `posted_at` = now at posting time

## Cross-Tenant Integrity

- All query sets use `.for_tenant(request.tenant_id)`
- Customer FK and settings account FKs are validated at the serializer boundary using tenant-scoped related fields (Feature 008 pattern)
- The posting service wraps the invoice status update and journal entry creation in `transaction.atomic()` so any failure rolls back all writes