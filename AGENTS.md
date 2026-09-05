<!-- SPECKIT START -->
Implementation plan: specs/011-purchases-payables/plan.md

Current phase: IMPLEMENTATION COMPLETE — Feature 011 (Purchases & Accounts Payable) fully implemented (backend + frontend + tests), regression green (223 backend tests), committed via auto-commit hook.

## What This Feature Does

Purchases & Accounts Payable — record vendor purchases against an AP workflow that integrates directly with the Accounting system: Vendor → Purchase Invoice → Accounts Payable → Payment → Journal Entry. This is the purchasing-side equivalent of Features 009 + 010, following the existing architecture rather than duplicating it. Posting a purchase invoice atomically books a single balanced Journal Entry (Dr configured Expense, Dr configured Input VAT, Cr configured Accounts Payable) with reference `PUR-INV-{number}`; posting a vendor payment books the reverse AP cash entry (Dr Accounts Payable, Cr the payment's cash/bank Asset account) with reference `PAY-PUR-{invoice.number}-{payment.number}`. The Feature 010 `Payment` model/service is generalized with a `direction` field (`Receivable`/`Payable`, default Receivable) so receipts and vendor payments share one engine; the sales payments API is unchanged.

## Generated Artifacts

- `specs/011-purchases-payables/spec.md` — Feature specification (draft)
- `specs/011-purchases-payables/plan.md` — Implementation plan (draft)
- `specs/011-purchases-payables/research.md` — Technical research (draft)
- `specs/011-purchases-payables/data-model.md` — Data model (draft)
- `specs/011-purchases-payables/contracts/purchases-api.md` — Purchases API contracts (draft)
- `specs/011-purchases-payables/contracts/payments-api.md` — Generalized payment API contracts (draft)
- `specs/011-purchases-payables/quickstart.md` — Validation scenarios (verified)
- `specs/011-purchases-payables/tasks.md` — Implementation tasks (all complete)
- `specs/011-purchases-payables/checklists/requirements.md` — Spec quality checklist (verified full)
- `specs/011-purchases-payables/report.md` — Implementation report

## Key Decisions (locked in the plan)

- New `apps/purchases` app (already registered in INSTALLED_APPS) with `Vendor`, `PurchaseInvoice`, `PurchaseInvoiceLine`, `PurchaseSettings`.
- New `PurchaseSettings` mirror of `SalesSettings` (AP=Liability, Expense=Expense, Input VAT=Asset); SalesSettings untouched.
- Generalize `Payment` (sales migration `0003`): `direction` (default Receivable), `invoice` nullable, additive `purchase_invoice` FK, exact-one-invoice check constraint.
- Purchase invoice lifecycle Draft → Posted; cancelled/void deferred.
- Posting requires AP+Expense accounts always and Input VAT when `tax > 0` (balanced JEs; deviates from sales' optional-VAT path — sales unchanged).
- Payment JE for vendors is **Dr AP / Cr cash** (money out reduces both; the brief's illustrative directions were reversed — documented deviation).

## Next Steps (after review)

- None — the feature is complete. Review the report, then plan the next feature (AP aging / vendor statements, Feature 012 inventory/COGS, or ledger editing of posted entries).

## Quick Reference

- Backend tests: `cd backend && py -m pytest apps/ -q` (223 passing = 153 baseline + 70 purchases; DJANGO_SETTINGS_MODULE=config.settings.test)
- Planned purchases URLs: `api/v1/purchases/vendors/`, `api/v1/purchases/invoices/` (+ `{id}/post_invoice/`), `api/v1/purchases/payments/` (+ `{id}/post_payment/`), `api/v1/purchases/settings/current/`
- Existing sales URLs (unchanged): `api/v1/sales/customers/`, `api/v1/sales/invoices/`, `api/v1/sales/payments/`, `api/v1/sales/settings/current/`
- Payment code being generalized: `backend/apps/sales/models.py` (`Payment`), `services.py` (`PaymentService`)
- Frontend: `npm run build` and `npm run lint` in `frontend/` (16 pre-existing problems in earlier feature files; new files must stay clean)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->