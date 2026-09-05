# Quickstart: Payments & Receipts (Feature 010)

Validation scenarios to run during implementation. Requires a running API (Feature 009 tenant + sales invoice + sales settings already configured per Feature 009 quickstart).

Test settings: `DJANGO_SETTINGS_MODULE=config.settings.test`. Authed requests carry `Authorization: Bearer <token>` for a tenant with `Admin`/`Accountant` role. Money amounts are decimal strings.

## Scenario 1 — Record and post a full payment

1. Post a sales invoice of `10000.0000` (Feature 009): `POST /api/v1/sales/invoices/{id}/post_invoice/`.
2. Verify the invoice now reports outstanding:
   `GET /api/v1/sales/invoices/{id}/` → `"paid_amount": "0.0000"`, `"outstanding_balance": "10000.0000"`.
3. Create a draft payment:
   `POST /api/v1/sales/payments/` with `{ "number": "PAY-0001", "invoice": "{id}", "payment_date": "2026-09-05", "amount": "10000.0000", "method": "Bank Transfer", "cash_account": "{asset_account_id}" }` → `201`, `status: "Draft"`.
4. Post it: `POST /api/v1/sales/payments/{id}/post_payment/` → `200`, `status: "Posted"`, `journal_entry` populated.
5. Re-check invoice: `outstanding_balance: "0.0000"`, `paid_amount: "10000.0000"`.
6. Verify one balanced JE on the ledger for account `{asset_account_id}` showing a `PAY-INV-…-PAY-0001` debit of `10000.0000` and a corresponding credit on the AR account.

## Scenario 2 — Partial and multiple payments

1. Invoice of `10000.0000` (posted).
2. Post payment `PAY-0001` amount `4000.0000` → invoice `outstanding_balance: "6000.0000"`.
3. Post payment `PAY-0002` amount `6000.0000` → invoice `outstanding_balance: "0.0000"`.
4. Attempt `PAY-0003` amount `1.0000` → rejected `400` "Amount exceeds the outstanding balance.", no JE.

## Scenario 3 — Idempotency

1. Post the same payment twice: second `POST /api/v1/sales/payments/{id}/post_payment/` → `400 "Payment is already posted."`, and the journal has exactly one entry for it.

## Scenario 4 — Overpayment is never booked

1. New invoice `10000.0000` (posted), draft payment `amount: "10001.0000"` → `400` at create.
2. Draft payment `amount: "9999.0000"` created, invoice edited to `10000.0000` through payment form → post fails `400` if amount now exceeds outstanding (validated again at post).

## Scenario 5 — No payment on a draft invoice

1. Create (do **not** post) an invoice.
2. Attempt `POST /api/v1/sales/payments/` → `400` "Only posted invoices can receive payments."

## Scenario 6 — Tenant isolation

1. As tenant B, attempt to create a payment referencing tenant A's posted invoice or account → `400`/`404` generic errors, no data leak; a foreign payment id → `404`.

## Scenario 7 — Configuration guard

1. Clear `accounts_receivable` in Sales Settings.
2. Draft creation still works (`201`); posting the draft → `400` "Sales accounting settings are not configured."
3. Restore `accounts_receivable` (active Asset), post again → `200`.

## Automated verification

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
py -m pytest apps/sales/tests/test_payments_api.py apps/accounts/tests/ apps/accounting/tests/ apps/sales/tests/ -v
```

Expected: all new payment tests + the 130-test regression baseline pass.