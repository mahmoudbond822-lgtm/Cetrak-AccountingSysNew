# Feature 009 — Sales Cycle (Foundation): Final Report

Status: IMPLEMENTATION COMPLETE — all backend tests passing, frontend builds.

## Summary

Implemented the Sales Cycle foundation: tenant-isolated Customers, Draft/Posted Sales
Invoices with line-based `Decimal` money math, and secure posting that generates a single
balanced Journal Entry through an admin-configured per-tenant account mapping. Posting is
idempotent and transactional; every invoice reference and account mapping is validated
against the active tenant. No accounts are ever hard-coded.

## Files Changed / Added

### Backend (new — `backend/apps/sales/`)
- `models.py` — `Customer`, `SalesInvoice`, `SalesInvoiceLine`, `SalesSettings`
- `migrations/0001_initial.py` — generated with `makemigrations sales`
- `permissions.py` — `CanViewSales` (Admin/Accountant/Manager), `CanManageSales` +
  `CanPostSalesInvoice` (Admin/Accountant), `CanConfigureSales` (Admin)
- `services.py` — `SalesSettingsService`, `SalesInvoiceService` (draft CRUD, totals in
  `Decimal`, posting), `compute_line_totals`
- `serializers.py` — `CustomerSerializer`, `SalesSettingsSerializer`,
  `SalesInvoiceLineSerializer`, `SalesInvoiceSerializer`, `SalesInvoicePostSerializer`
  (reuses Feature 008 `TenantScopedAccountField`)
- `views.py` — `CustomerViewSet`, `SalesInvoiceViewSet` (incl. `post_invoice` action),
  `SalesSettingsViewSet`
- `urls.py` — routers for `customers/`, `invoices/`, `settings/`
- `tests/test_sales_api.py` — 41 tests (permissions, settings, customers, invoices,
  posting, multi-tenant isolation, no-disclosure)

### Backend (modified)
- `backend/config/urls.py` — included `apps.sales.urls` under `api/v1/sales/`

### Frontend (new)
- `src/services/salesService.js` — customers/invoices/settings API wrapper
- `src/components/Layout/SalesNav.jsx` — Customers / Invoices / Settings tabs
- `src/components/sales/customers/CustomerModal.jsx`
- `src/components/sales/invoices/InvoiceForm.jsx` (line rows, running totals)
- `src/pages/sales/CustomersPage.jsx`, `InvoicesPage.jsx`, `SalesSettingsPage.jsx`

### Frontend (modified)
- `src/App.jsx` — routes for `/sales/customers`, `/sales/invoices`, `/sales/settings`

### Docs / Config
- `specs/009-sales-cycle/*` (spec, plan, research, data-model, quickstart, tasks,
  contracts, checklists — authored/revised in this feature)
- `AGENTS.md` — phase marker updated to Feature 009
- `.specify/feature.json` — points at `specs/009-sales-cycle`

## Migrations

- `apps.sales.migrations.0001_initial` — creates `sales_customer`, `sales_invoice`,
  `sales_invoiceline`, `sales_settings` plus unique constraints
  (`unique_customer_code_per_tenant`, `unique_invoice_number_per_tenant`,
  `unique_sales_settings_per_tenant`) and indexes.

## API Surface (`api/v1/sales/`)

| Endpoint | Method | Permission | Notes |
|---|---|---|---|
| `customers/` | GET/POST | View / Manage | POST is idempotent on `(tenant, code)` |
| `customers/{id}/` | GET/PATCH/DELETE | View / Manage | DELETE = deactivate (204) |
| `invoices/` | GET/POST | View / Manage | POST computes totals |
| `invoices/{id}/` | GET/PATCH/DELETE | View / Manage | drafts only |
| `invoices/{id}/post_invoice/` | POST | PostSalesInvoice | creates balanced JE |
| `settings/current/` | GET/PUT | Admin | AR/Revenue/VAT mapping |

Money is `DecimalField(max_digits=19, decimal_places=4)`; JSON returns
`"100.0000"`-style strings.

## Accounting Integration

Posting (inside `transaction.atomic()`, idempotent via `posted_journal` OneToOne):

- Requires a complete, active, same-tenant account mapping (AR=Asset, Revenue=Revenue,
  VAT=Liability); otherwise → 400 with a generic, non-disclosing message and full rollback.
- Entry: `reference = "SALES-INV-{number}"`, `posted=True`, `date = invoice_date`; lines
  `Dr AR = total`, `Cr Revenue = subtotal − discount`, `Cr VAT = tax` (VAT line omitted
  when tax is 0). Balanced by construction.
- Failed/duplicate post → 400, zero journal entries, invoice unchanged.

## Frontend

Sales UI follows the existing design system (inline styles, `Table`/`Modal`/`Button`/
`Input`, `AccountSelect` from journal). Role gating mirrored on the client; server 403s are
authoritative. `npm run build` passes. Lint: the 16 remaining `npm run lint` errors are all
pre-existing in earlier feature files (`AccountsPage`, `AccountSelect`, `TenantSwitcher`,
`TenantSelectPage`, `JournalPage`, `LedgerPage`); the new sales files add zero lint errors.

## Security

- Every query scoped with `objects.for_tenant(request.tenant_id)`; cross-tenant object
  lookups 404 (no existence leak).
- Account FKs validated in serializers (`TenantScopedAccountField`) and again at post time
  (tenant ownership + `is_active` + type) — defense in depth.
- Safe errors: posting failures never surface account names/tenant names; no disclosure.
- Role boundaries verified by tests (`Manager` view-only, settings `Admin`-only).

## Tests

- 130 backend tests pass: 89 pre-existing (accounts + accounting) + 41 new sales tests.
  Command: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/ -q`
- Coverage includes: totals math, validation, duplicate numbers/codes, cross-tenant
  injection attempts, idempotent posting, immutability after posting, rollback safety,
  no-disclosure on errors, role matrix, zero-tax posting.

## Recorded Deviations

1. Post action URL is `/post_invoice/` (not `/post/`).
2. Duplicate customer code on create → 200 with existing customer (idempotent
   merge-semantics per BRD), not 400.
3. Edits/deletes of posted invoices → 400 with safe message (spec allows 400).
4. `tasks.md` T051: lint caveat as documented above.

## Limitations / Follow-ups (deferred, per spec)

- Quotations, sales orders, payments/collections, cash sales, and inventory — out of scope.
- Multi-currency — blocked on ledger support (single-currency assumed).
- Estimating/rounding policy across a chart with mixed decimal places is unchanged.
- Posting accounting mapping is a single revenue/VAT pair (no per-line splitting).

## Recommended Next Feature

Payments/Receipts against posted invoices (apply cash to `Accounts Receivable`) — the
natural continuation of the posting flow and the first thing that gives the AR account
movement on behalf of real cash.