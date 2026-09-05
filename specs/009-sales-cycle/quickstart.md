# Quickstart: Sales Cycle (Foundation)

**Purpose**: Manual validation scenarios for Feature 009. Each scenario is a complete end-to-end check against a running API.

**Prerequisites**: Backend running (Django test server or `docker compose up`), a logged-in workspace with at least one Asset, Revenue, and Liability account in the chart of accounts.

## Setup

1. Log in as an **Admin** and capture the tenant id.
2. In the Chart of Accounts, create (if missing): an Asset account "Accounts Receivable", a Revenue account "Sales Revenue", a Liability account "VAT Payable".

## Scenario 1 — Configure the sales accounting mapping (US4)

1. As Admin, `GET /api/v1/sales/settings/current/` → returns all-null mapping.
2. `PUT /api/v1/sales/settings/current/` with the three account ids → 200, mapping saved.
3. As Accountant, `GET /api/v1/sales/settings/current/` → 403 (Admin-only).

## Scenario 2 — Customer management (US1)

1. As Accountant, `POST /api/v1/sales/customers/` with `{code: "C-001", name: "Acme Trading"}` → 201.
2. Create `C-002` in a **second tenant** → allowed (codes are per-tenant).
3. Try `POST` `C-001` again in the first tenant → the existing customer is returned (200, merge-semantics, idempotent create).
4. As Manager, `GET /api/v1/sales/customers/` → 200 (view allowed), but `POST` → 403.
5. From the second tenant, `GET /api/v1/sales/customers/{C-001 id}/` → 404-equivalent, no Acme data disclosed.

## Scenario 3 — Draft invoice and calculations (US2)

1. As Accountant, `POST /api/v1/sales/invoices/` with customer `C-001`, `number: "INV-2026-001"`, one line `{quantity: "2", unit_price: "100.00", tax_rate: "15.00"}` → 201 Draft.
2. Verify computed `subtotal` = `200.00`, `tax` = `30.00`, `total` = `230.00`.
3. Try a line with `quantity: "0"` → 400; with `unit_price: "-5"` → 400.
4. Try duplicate `number: "INV-2026-001"` → 400. In the second tenant the same number succeeds.
5. Try an invoice referencing the second tenant's customer → 400, and no invoice row exists.
6. `PATCH` the draft (change quantity to 3) → 200, totals recompute (`subtotal` = `300.00`).

## Scenario 4 — Posting and accounting integration (US3)

1. As Accountant, `POST /api/v1/sales/invoices/{id}/post_invoice/` → 200; invoice `status = "Posted"`.
2. Open the accounting Journal Entries list → one entry `SALES-INV-INV-2026-001`, already posted, balanced.
3. Open the Ledger for "Accounts Receivable" → debit equals invoice `total`. "Sales Revenue" ledger credit equals subtotal − discount.
4. `POST .../post_invoice/` again → 400 (already posted), and no second journal entry exists.
5. Run the Trial Balance → debits still equal credits.

## Scenario 5 — Failure safety (rollback)

1. Create a draft invoice, then `PUT /api/v1/sales/settings/` mapping to an **inactive** account (or clear it).
2. `POST .../post/` → 400; invoice still `Draft`; Journal Entries count unchanged; Trial Balance unchanged.

## Scenario 6 — Cross-tenant isolation review

1. From tenant B, attempt to access tenant A's customers, invoices, and settings → no data returned, generic errors only.
2. Attempt to write tenant A's account ids into tenant B's settings → 400, no partial save.

## Expected Outcome

All scenarios complete with no cross-tenant reads/writes, no unbalanced journal entries, no duplicate journal entries, and no partial writes after any failure.