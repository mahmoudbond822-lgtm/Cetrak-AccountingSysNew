<!-- SPECKIT START -->
Implementation plan: specs/010-payments-receipts/plan.md

Current phase: IMPLEMENTATION COMPLETE — Feature 010 (Payments & Receipts) shipped. Backend 153 tests passing, frontend builds, new files lint-clean. See `specs/010-payments-receipts/report.md`.

## What This Feature Does

Payments & Receipts — record customer payments against **posted** sales invoices. Posting a payment atomically books a single balanced Journal Entry (Dr the payment's cash/bank Asset account, Cr the tenant's configured `accounts_receivable` from Sales Settings), locks the invoice row to prevent overpayment races, and is idempotent (no double posting). Partial and multiple payments are supported with a derived outstanding balance (`total − Σ posted`); overpayment is always rejected. Draft payments are editable/deletable; posted payments are immutable (reversal deferred; manual reversing Journal Entry is the documented correction path).

## Generated Artifacts

- `specs/010-payments-receipts/spec.md` — Feature specification
- `specs/010-payments-receipts/plan.md` — Implementation plan
- `specs/010-payments-receipts/research.md` — Technical research
- `specs/010-payments-receipts/data-model.md` — Data model
- `specs/010-payments-receipts/contracts/payments-api.md` — API contracts
- `specs/010-payments-receipts/quickstart.md` — Validation scenarios
- `specs/010-payments-receipts/tasks.md` — Implementation tasks (all complete)
- `specs/010-payments-receipts/report.md` — Final implementation report
- `specs/010-payments-receipts/checklists/requirements.md` — Spec quality checklist (all verified)

## Next Steps
- Backend tests all green (153); frontend build passes. Suggested follow-ups: customer statements/AR aging, ledger entry correction/reversal, payments receipt PDF, auto-sequenced payment numbers.

## Quick Reference
- Backend tests: `cd backend && py -m pytest apps/ -q` (153 passing; DJANGO_SETTINGS_MODULE=config.settings.test)
- Payments URLs (live): `api/v1/sales/payments/`, `api/v1/sales/payments/{id}/`, `api/v1/sales/payments/{id}/post_payment/`
- Sales URLs (existing): `api/v1/sales/customers/`, `api/v1/sales/invoices/`, `api/v1/sales/invoices/{id}/post_invoice/`, `api/v1/sales/settings/current/`
- Payment code: `backend/apps/sales/models.py` (`Payment`), `services.py` (`PaymentService`), `serializers.py`, `views.py`, `tests/test_payments_api.py`; frontend `frontend/src/pages/sales/PaymentsPage.jsx`, `components/sales/payments/PaymentForm.jsx`
- Frontend: `npm run build` and `npm run lint` in `frontend/` (16 pre-existing problems in earlier feature files; new payment files are clean)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->