# Quickstart & Validation: Purchases & Accounts Payable (Feature 011)

> Validate feature 011 without guessing what success looks like. Numbers are exact; a passing scenario uses **these** values and these error messages.

## Setup

1. Ensure Feature 009 (Sales + journal posting) and Feature 010 (Payments) are present — the `Payment` model is generalized here.
2. Backend up (`cd backend && uv run python manage.py runserver` or the Docker Compose stack in `infra/`).
3. Login as an Admin/Accountant for tenant A; JWT from the standard auth endpoint.

## Checklist Scenarios

### Vendors

1. **Create** → `POST /api/v1/purchases/vendors/` `{code: "V001", name: "Alpha Supplies Ltd", tax_id: "GB 123 4567 89"}` → `201`, `is_active=true`.
2. **Duplicate code** → same payload again → `400` `{"code": ["Vendor code already exists."]}`.
3. **Edit** → `PATCH …/vendors/{id}/` `{phone: "+44 20 7946 0001"}` → `200`.
4. **Cross-tenant** → as tenant B → `GET …/vendors/{tenantA_id}/` → `404` `{"detail": "Vendor not found."}`.
5. **Delete with invoices** (after scenario below posts invoices) → `DELETE` → `204`; `GET` → list excludes it / `is_active=false`.

### Purchase invoice + posting

1. **Configure accounts**: create/post a Liability `3001 AP`, Expense `6001 Purchases`, Asset `1205 Input VAT` (API or fixture). `POST /api/v1/purchases/settings/current/` with their ids → `200`.
2. **Create draft** → `POST /api/v1/purchases/invoices/`:
   ```json
   {"number": "PUR-2026-001", "vendor_id": "<V001>", "invoice_date": "2026-09-01",
    "due_date": "2026-10-01",
    "lines": [{"description": "Steel beams", "quantity": "10", "unit_price": "1000", "tax_rate": "15"}]}
   ```
   → `201` `subtotal=10000.0000, tax=1500.0000, total=11500.0000, status=Draft`.
3. **Anti-cheese**: quantity "0" → `400`; tax_rate "150" → `400`; `PUR-2026-001` again → `400` number exists.
4. **Post** → `POST …/invoices/{id}/post_invoice/` → `200`, `status=Posted`.
   - Verify Journal: `GET /api/v1/accounting/journal-entries/` find `reference="PUR-INV-PUR-2026-001"` → exactly **one** JE, balanced: Dr Expense 10000.0000, Dr Input VAT 1500.0000, Cr AP 11500.0000.
5. **Re-post** → `400` `"Only draft purchase invoices can be posted."`; JE count unchanged.

### Payments (Payable) — the 20,000 / 7,000 / 13,000 AP walkthrough

1. Post a purchase invoice `PUR-2026-002`, `total=20000.0000` (e.g. 20 × 1000 @ 0% tax).
   → list shows `paid_amount=0.0000, outstanding_balance=20000.0000`.
2. **Payment 1** → `POST /api/v1/purchases/payments/` `{number:"PAY-001", purchase_invoice_id:"<PUR-002>", cash_account_id:"<Bank>", payment_date:"2026-09-05", amount:"7000.0000"}` → `201`, `status=Draft`; then `POST …/payments/{id}/post_payment/` → `200`, `status=Posted`.
   - JE: `PAY-PUR-PUR-2026-002-PAY-001` — **Dr AP 7000.0000, Cr Bank 7000.0000** (correct money-out direction; do NOT accept a reversed/Dr-Cash entry here).
   - Invoice → `paid_amount=7000.0000, outstanding_balance=13000.0000`.
3. **Payment 2** → `PAY-002` `amount:"13000.0000"` → post → outstanding `0.0000`.
4. **Overpayment at create** → `PAY-003` `amount:"1.0000"` → `400` `{"amount": ["Amount exceeds the outstanding balance."]}`.
5. **Posted-only** → payment against draft `PUR-2026-003` → `400` `"Only posted purchase invoices can be paid."`.
6. **Idempotent post** → re-post `PAY-002` → `400` `"Only draft payments can be posted."`; JE count for `PAY-002` unchanged.

### Settings / config guards

1. Remove `input_vat` from settings; post a new invoice with `tax_rate=15` → `400` `"Purchase accounting settings are not configured."`; no JE.
2. Point `accounts_payable` at an Expense account → post → `400` `"Invalid account type for purchase accounting settings."`.
3. As-tests: cross-tenant `vendor_id`/`cash_account_id`/invoice → generic `404`-flavored errors below.

## Full regression

`cd backend && py -m pytest apps/ -q` → **153 (baseline) + new purchases tests, all green.**

## Frontend smoke

1. `Purchases → Vendors`: create/edit/deactivate a vendor.
2. `Purchases → Purchase Invoices`: create, edit draft lines, post; VAT totals recompute per line.
3. `Purchases → Payments`: pick a **Posted** invoice, see outstanding, record/delete drafts, post, see outstanding drop to 0.
4. `npm run build` passes; new files `npm run lint`-clean.

## Known/future limitations (by design)

- Single expense account at posting (no per-line mapping / Inventory COGS — Feature 012).
- Input VAT required when `tax > 0` (balanced-JE invariant; stricter than sales' optional-VAT path — documented deviation, do not change sales).
- Cancelled/Void purchase invoices and payment reversal deferred; manual reversing Journal Entry is the correction path.
- Numbering is user-supplied and unique per tenant.
- Payment accounting note: paying vendors is **Dr AP / Cr cash** — the brief's illustrative "Dr cash / Cr AP" was reversed; correct direction enforced and tested.