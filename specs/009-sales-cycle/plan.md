# Implementation Plan: Sales Cycle (Foundation)

**Branch**: `main` | **Date**: 2026-09-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-sales-cycle/spec.md`

## Summary

Build the Sales module foundation (Customers + Sales Invoices) tightly integrated with the existing Accounting module. Customers and invoices are tenant-isolated. Posting an invoice creates a single balanced journal entry (Dr Accounts Receivable, Cr Sales Revenue, Cr VAT Payable) using a per-tenant, admin-configured account mapping — no hard-coded account IDs. All writes are transactional and idempotent. Sales Quote/Order and Payments are deferred to keep the feature an independently testable MVP.

## Technical Context

**Language/Version**: Python 3.14 / Django 6.0.4, Django REST Framework; JavaScript/React 19 + Vite frontend

**Primary Dependencies**: Django, DRF, Simple JWT, pytest/Django test runner, PostgreSQL in production, SQLite in-memory for tests

**Storage**: New tables under `apps/sales` (`sales_customer`, `sales_invoice`, `sales_invoiceline`, `sales_settings`). The `sales` app already exists in `INSTALLED_APPS`.

**Testing**: New tests in `backend/apps/sales/tests/test_sales_api.py`; full regression run of `apps/accounts/tests/` and `apps/accounting/tests/`.

**Target Platform**: Web service backend behind the existing tenant middleware; React frontend for the sales UI.

**Project Type**: Multi-tenant web application with backend API and frontend client.

**Performance Goals**: Sales endpoints add no additional blocking work beyond existing accounting query patterns; posting performs a bounded number of atomic writes within a single transaction.

**Constraints**: No new dependencies; no changes to existing accounting APIs; no deployment/Render work; tenant isolation follows Feature 008 patterns; money stays in `Decimal`; no hard-coded tenant or account IDs; minimal migrations (one for the sales app).

## Constitution Check

*GATE: Must pass before implementation research. Re-check after design.*

- **Multi-Tenancy (NON-NEGOTIABLE)**: PASS. Every sales model is `TenantScopedModel`; every endpoint is scoped by `for_tenant`; every FK (customer, mapping accounts) is validated tenant-scoped at the serializer boundary exactly as Feature 008 established.
- **Accounting Integrity (CRITICAL)**: PASS. Posting creates a balanced journal entry by construction and reuses the existing accounting models, services, and DB constraints. Posted invoices are immutable.
- **API Rules**: PASS. RESTful routers under `/api/v1/sales/`, standard DRF error JSON, all endpoints authenticated.
- **Code Standards**: PASS. Business logic in `apps/sales/services.py`; viewsets stay thin. No fat views.
- **AI Safety Rules**: PASS. No AI behavior introduced.
- **Security**: PASS. Middleware-level isolation plus serializer-level reference validation; safe errors that never disclose other tenants' data.
- **Performance**: PASS. Small bounded transaction on post; indexed tenant/customer/number columns.
- **MVP Discipline**: PASS. Scope limited to Customers + Invoices + Posting + Settings; Quote/Order/Payments/Inventory deferred and documented.

Post-design re-check: PASS. Scope, artifacts, and constraints are unchanged from the decisions above.

## Project Structure

### Documentation (this feature)

```text
specs/009-sales-cycle/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── sales-api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── apps/sales/
│   ├── models.py            # SalesSettings, Customer, SalesInvoice, SalesInvoiceLine
│   ├── migrations/
│   │   └── 0001_initial.py  # generated
│   ├── services.py          # CustomerService, SalesInvoiceService (incl. posting)
│   ├── serializers.py       # tenant-scoped related fields, invoice line/totals validation
│   ├── views.py             # CustomerViewSet, SalesInvoiceViewSet, SalesSettingsView
│   ├── permissions.py       # CanViewSales, CanManageSales, CanPostSalesInvoice, CanConfigureSales
│   ├── urls.py              # router under /api/v1/sales/
│   └── tests/
│       └── test_sales_api.py
└── config/
    ├── urls.py              # include sales.urls
    └── settings/base.py     # unchanged (sales already enabled)

frontend/src/
├── services/salesService.js
├── components/sales/SalesNav.jsx
├── components/sales/customers/CustomerForm.jsx
├── components/sales/invoices/InvoiceForm.jsx
├── components/sales/invoices/InvoiceLineRow.jsx
├── pages/sales/CustomersPage.jsx
├── pages/sales/InvoicesPage.jsx
├── pages/sales/InvoiceFormPage.jsx
├── pages/sales/SalesSettingsPage.jsx
└── App.jsx                  # add routes
```

**Structure Decision**: Add the sales app as its own Django app (already registered) with models/services/serializers/views/permissions mirroring the accounting app layout. Keep accounting untouched except for nothing (no accounting source changes required; the posting path only creates accounting records through existing model APIs).

## Implementation Approach

1. **Phase A — Data model & migrations**: Define models with decimal money fields, tenant constraints, and indexes; generate `0001_initial`. Enforce at the service boundary: unique code/number per tenant, positive quantities, tax rate 0–100, discount ≤ subtotal, total > 0, description on every line.
2. **Phase B — Permissions**: `CanViewSales`, `CanManageSales`, `CanPostSalesInvoice`, `CanConfigureSales` matching accounting conventions.
3. **Phase C — Services**: `CustomerService` and `SalesInvoiceService` (create draft, totals recomputation in `Decimal`, post within `transaction.atomic()`).
4. **Phase D — API**: serializers with tenant-scoped FK fields (Feature 008 pattern), viewsets, router registration, URL include. Safe error handling per Feature 008.
5. **Phase E — Backend tests**: customer CRUD + isolation + permissions; invoice create/validate/calculate/isolation/cross-tenant customer rejection; posting success/balanced/duplicate/missing mapping/failed reference rollback/cross-tenant protection; permissions matrix. Follow the existing `APITestCase` + `_headers` helper pattern.
6. **Phase F — Full regression**: run `apps/accounts/tests/` + `apps/accounting/tests/` + `apps/sales/tests/` together; everything must pass.
7. **Phase G — Frontend**: `salesService.js`, `SalesNav`, customers and invoices pages + forms + post action, admin settings page; wire routes; verify `npm run build` and `npm run lint`.
8. **Phase H — Security review**: re-run isolation scenarios end-to-end; confirm no cross-tenant disclosure in any sales error path.
9. **Phase I — Documentation**: quickstart validation, requirements checklist, AGENTS.md phase update, final feature report.

## Complexity Tracking

No constitution violations are required. The only new source of complexity is the per-tenant sales accounting settings, which is justified because it is the mechanism that prevents hard-coded account IDs (a hard requirement of this feature and of accounting integrity).