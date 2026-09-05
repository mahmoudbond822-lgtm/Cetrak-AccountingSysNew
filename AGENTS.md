<!-- SPECKIT START -->
Implementation plan: specs/010-payments-receipts/plan.md

Current phase: PLANNING — Feature 010 (Payments & Receipts) spec artifacts drafted; awaiting approval before implementation.

## What This Feature Does

Payments & Receipts — record customer payments against **posted** sales invoices. Posting a payment atomically books a single balanced Journal Entry (Dr the payment's cash/bank Asset account, Cr the tenant's configured `accounts_receivable` from Sales Settings), locks the invoice row to prevent overpayment races, and is idempotent (no double posting). Partial and multiple payments are supported with a derived outstanding balance (`total − Σ posted`); overpayment is always rejected. Draft payments are editable/deletable; posted payments are immutable (reversal deferred; manual reversing Journal Entry is the documented correction path).

## Generated Artifacts

- `specs/010-payments-receipts/spec.md` — Feature specification
- `specs/010-payments-receipts/plan.md` — Implementation plan
- `specs/010-payments-receipts/research.md` — Technical research
- `specs/010-payments-receipts/data-model.md` — Data model
- `specs/010-payments-receipts/contracts/payments-api.md` — API contracts
- `specs/010-payments-receipts/quickstart.md` — Validation scenarios
- `specs/010-payments-receipts/tasks.md` — Implementation tasks
- `specs/010-payments-receipts/checklists/requirements.md` — Spec quality checklist

## Next Steps
- `/speckit.tasks` — Generate implementation tasks
- `/speckit.implement` — Execute the implementation (after plan/tasks approval)

## Quick Reference
- Backend tests: `cd backend && py -m pytest apps/accounts/tests/ apps/accounting/tests/ apps/sales/tests/ -v`
- Test settings: DJANGO_SETTINGS_MODULE=config.settings.test
- Payment URLs (planned): `api/v1/sales/payments/`, `api/v1/sales/payments/{id}/`, `api/v1/sales/payments/{id}/post_payment/`
- Sales URLs (existing): `api/v1/sales/customers/`, `api/v1/sales/invoices/`, `api/v1/sales/invoices/{id}/post_invoice/`, `api/v1/sales/settings/current/`
- Frontend: `npm run build` and `npm run lint` in `frontend/` (lint has pre-existing failures in earlier feature files; new sales files are clean)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->