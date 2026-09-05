# Feature 010 — Payments & Receipts: Final Report

Status: IMPLEMENTATION COMPLETE — all backend tests passing, frontend builds, new files lint-clean.

## Summary

Implemented Payments & Receipts: recording customer payments against **posted** sales
invoices. Posting a payment atomically books a single balanced Journal Entry (Dr the
payment's cash/bank **Asset** account, Cr the tenant's configured `accounts_receivable`
from Sales Settings), locks the invoice row to prevent overpayment races, and is
idempotent (no double posting). Partial and multiple payments are supported with a derived
outstanding balance (`total − Σ posted`); overpayment is always rejected. Draft payments
are editable/deletable; posted payments are immutable (reversal deferred; a manual
reversing Journal Entry is the documented correction path).

## Files Changed / Added

### Backend (new)
- `backend/apps/sales/models.py` — `Payment` (`sales_payment`): `number`, `invoice` FK
  PROTECT, `payment_date`, `amount` Decimal(19,4), `method` (Cash/Bank Transfer/Card/Check),
  `cash_account` FK Account PROTECT, `reference`, `notes`, `status` (Draft/Posted),
  `journal_entry` OneToOne PROTECT null, `posted_at`; `unique (tenant, number)`
  (`unique_payment_number_per_tenant`); indexes `(tenant, status)` and `(invoice)`.
- `backend/apps/sales/migrations/0002_payment.py` — generated; no schema changes outside
  `apps/sales`.
- `backend/apps/sales/services.py` — `PaymentService`: `invoice_paid_amount`,
  `invoice_outstanding`, `create_draft`, `update_draft`, `delete_draft`, `post_payment`
  (all Decimal-only, no `float`).
- `backend/apps/sales/serializers.py` — `TenantScopedPostedInvoiceField`,
  `PaymentSerializer` (nested invoice summary incl. customer/total/paid/outstanding);
  additive read-only `paid_amount` + `outstanding_balance` on `SalesInvoiceSerializer`.
- `backend/apps/sales/views.py` — `PaymentViewSet` (list/create/retrieve/partial_update/
  destroy + `post_payment` action; per-action permissions; `?status=` / `?invoice=` filters).
- `backend/apps/sales/urls.py` — `payments` router (basename `payment`).
- `backend/apps/sales/tests/test_payments_api.py` — 23 tests (happy path, partial/multiple,
  overpayment, guards, tenant isolation, account validation, settings validation, number
  uniqueness, permissions, no-disclosure).

### Frontend (new)
- `src/components/sales/payments/PaymentForm.jsx` — invoice picker (posted only, shows
  outstanding), amount with client-side ≤ outstanding check, method select, Asset
  cash-account select, reference/notes; new + edit modes.
- `src/pages/sales/PaymentsPage.jsx` — list (number, customer, invoice, date, method,
  amount, status), new/create-modal, delete draft, post-confirm dialog.

### Frontend (modified)
- `src/services/salesService.js` — `getPayments/getPayment/createPayment/updatePayment/
  deletePayment/postPayment`.
- `src/App.jsx` — route `/sales/payments`.
- `src/components/Layout/SalesNav.jsx` — "Payments" tab.

### Docs
- `specs/010-payments-receipts/tasks.md`, `checklists/requirements.md` — marked complete.
- `AGENTS.md` — phase marker updated to Feature 010 IMPLEMENTATION COMPLETE.

## Migrations

- `apps.sales.migrations.0002_payment` — `sales_payment` with unique
  `unique_payment_number_per_tenant` and supporting indexes. `makemigrations --check
  --dry-run` and `migrate --check` both clean.

## API Surface (`api/v1/sales/`)

| Endpoint | Method | Permission | Notes |
|---|---|---|---|
| `payments/` | GET | View | filter `?status=`, `?invoice=` |
| `payments/` | POST | Manage | draft; rejected if > outstanding |
| `payments/{id}/` | GET | View | joined `invoice` summary object |
| `payments/{id}/` | PATCH | Manage | drafts only |
| `payments/{id}/` | DELETE | Manage | drafts only (204) |
| `payments/{id}/post_payment/` | POST | PostSalesInvoice | creates balanced JE |

## Accounting Integration

Posting (inside `transaction.atomic()`, invoice row locked with `select_for_update`,
idempotent via status guard + `(tenant, reference)` unique):

- Requires Sales Settings with an active, same-tenant **Asset** `accounts_receivable`;
  otherwise → 400 ("Sales accounting settings are not configured.") with full rollback.
- Entry: `reference = "PAY-INV-{invoice.number}-{payment.number}"`, `date = payment_date`,
  `description = "Payment {number} for invoice {invoice.number}"`; lines `Dr cash_account`,
  `Cr accounts_receivable` (each amount = balance). Balanced by construction.
- Outstanding recomputed under the row lock immediately before writing the JE; any
  overpayment → 400 and zero journal entries.
- Money stays `Decimal(19,4)` end to end; no `float`.

## Frontend

Payments UI follows the existing design system (inline styles, `Table`/`Modal`/`Button`/
`Input`). Role gating mirrored on the client; server 403s authoritative. The invoice
picker lists posted invoices with live outstanding; the form blocks client-side
overpayment before hitting the API (server remains authoritative). `npm run build` passes.
Lint: the 16 remaining `npm run lint` problems (15 errors + 1 warning) are all
pre-existing in earlier feature files; the new payment files add zero lint problems.

## Security

- Every query scoped with `objects.for_tenant(request.tenant_id)`; cross-tenant lookups
  404 (no existence leak).
- `cash_account` validated in the serializer and again at post time (tenant + `is_active`
  + Asset type) — defense in depth; a payment can never post to a foreign, inactive, or
  non-Asset account.
- Safe errors: posting failures never surface account/tenant names; no disclosure.
- Role boundaries verified by tests (Manager view-only, posting Admin/Accountant-only).

## Tests

- 153 backend tests pass: 130 pre-existing (accounts + accounting + sales foundation) +
  23 new payment tests.
  Command: `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/ -q`
- Coverage includes: balanced-JE posting, outstanding math across invoice/payment payloads,
  partial/multiple payments, overpayment at create and post, idempotent posting, draft
  edit/delete + posted immutability, cross-tenant injection attempts, missing/inactive AR
  config, number uniqueness, role matrix, no-disclosure.

## Recorded Deviations

1. `post_payment` URL is `/post_payment/` (mirrors `post_invoice` naming).
2. Frontend route: single list route `/sales/payments` with modal create/edit/post
   (mirrors customers/invoices); no separate `/new` or `/:id` routes (T-028).
3. Payment numbers are user-supplied (validated unique per tenant); auto-sequencing is
   deferred to a future feature, matching the invoices convention.

## Limitations / Follow-ups (deferred, per spec)

- Reversal of posted payments — deferred; documented correction path is a manual reversing
  Journal Entry.
- Checks clearing / bank reconciliation, payment allocation across refunds/credit notes —
  out of scope.
- Guest/unregistered cash sales and inventory — out of scope.
- Multi-currency — single-currency assumed (ledger limitation).

## Recommended Next Feature

Customer statements / AR aging (per-customer outstanding rollup) or editing/reversing
posted entries in the accounting ledger.