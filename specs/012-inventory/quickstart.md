# Quickstart: Inventory Management (Feature 012)

End-to-end validation scenarios (to be executed at implementation close-out against the live API). All money is `Decimal(19,4)`; every JE below is balanced (debit sum = credit sum).

Preconditions (from Features 009–011): a tenant with an active `Admin` user; chart of accounts includes Asset accounts (Cash/Bank, Inventory, Input VAT, Accounts Receivable) and expense accounts (COGS, Stock Adjustments, Purchases Expense); a customer and a vendor exist.

---

## Scenario A — Product catalog + settings

1. Create the product: `POST /api/v1/inventory/products/` `{"sku": "SKU-001", "name": "Widget 20mm", "unit": "pcs"}` → `201`, `is_active: true`.
   - `POST` same `sku` again → `400` "SKU already exists."
2. Duplicate: create `SKU-002 "Service line"` for a grab-bag test later.
3. Configure settings: `GET /api/v1/inventory/settings/current/` → returns the lazily-created `default_warehouse` row + three null accounts. `PUT` with:
   - `inventory_account` = an **Asset** account (e.g. "1100 Inventory"),
   - `cogs_account` = an **Expense** account (e.g. "5000 Cost of Goods Sold"),
   - `adjustments_account` = an **Expense** account (e.g. "5010 Stock Adjustments").
   - `PUT` with an Expense account in `inventory_account` → `400` "inventory_account account must be of type Asset." (server authoritative).
4. `GET /api/v1/inventory/warehouses/` → one active "Default" warehouse.

## Scenario B — Purchase posting books a stock receipt

1. Purchase invoice: `POST /api/v1/purchases/invoices/` with one line `{"product_id": <SKU-001>, "description": "Widget", "quantity": 10, "unit_price": 100, "tax_rate": 5}` and vendor, date → draft total 1050 (subtotal 1000, tax 50).
2. `POST …/{id}/post_invoice/`.
3. Verify:
   - JE `PUR-INV-{n}`: **Dr Inventory 1000, Dr Input VAT 50, Cr AP 1050** (balanced); invoice `Posted`.
   - `GET /api/v1/inventory/stock-balances/` → `quantity "10.0000"`, `value "1000.0000"`, `moving_avg_cost "100.0000"`.
   - `GET /api/v1/inventory/stock-movements/` → exactly one `Receipt` movement for `SKU-001` (qty `+10`, unit_cost `100`).

## Scenario C — Weighted-average valuation

1. Second purchase: 10 @ 120 → post → balance `qty 20 / value 2200 / avg 110`; one more Receipt movement.
2. Sales invoice: `POST /api/v1/sales/invoices/` one line `{"product_id": <SKU-001>, "description": "Widget", "quantity": 5, "unit_price": 150, "tax_rate": 5}`.
3. `POST …/{id}/post_invoice/`. Verify:
   - JE `SALES-INV-{n}`: **Dr AR 787.50, Cr Revenue 750.00, Cr VAT 37.50, Dr COGS 550.00, Cr Inventory 550.00** (balanced; COGS = 5 × 110).
   - Balance `qty 15 / value 1650 / avg 110` (unchanged avg — consumed at cost).
   - One `Issue` movement (`−5`, unit_cost `110`).

## Scenario D — Negative stock is impossible

1. Sales invoice for 16 units of `SKU-001` (only 15 on hand), posted → `400` "Insufficient stock." with **no** JE (`JournalEntry` count unchanged), no movement, no balance change. New draft can be edited/retried.

## Scenario E — Adjustments reconcile to the ledger

1. `POST /api/v1/inventory/adjustments/` `{"number": "ADJ-1", "adjustment_date": "…", "reason": "Count gain", "lines": [{"product_id": <SKU-001>, "quantity": 2}]}` → Draft.
2. `POST …/{id}/post_adjustment/` → JE `ADJ-INV-ADJ-1`: **Dr Inventory 220, Cr Adjustments 220**; balance `qty 17 / value 1870 / avg 110`.
3. Adjustment `ADJ-2` `quantity: -3` → post → JE **Dr Adjustments 330, Cr Inventory 330**; balance `qty 14 / value 1540`.
4. Adjustment `ADJ-3` `quantity: -100` → post → `400` "Insufficient stock." (no JE/movement).
5. **Ledger tie**: ledger balance of the Inventory account = +1000 +1200 −550 +220 −330 = **1540.0000 = balance.value**. ✓

## Scenario F — Service lines are unchanged (regression semantics)

1. Purchase invoice with only the `SKU-002` "service" grab-bag line (no `product_id`) → posting produces the Feature 011 JE exactly (Dr Expense, Dr Input VAT, Cr AP; no movements; no `StockBalance` row for SKU-002).
2. Sales invoice with only a grab-bag line → Feature 009 JE exactly (no COGS leg, no movements).

## Scenario G — Mixed stock + service + discount (single balanced JE)

1. Purchase invoice: stock line (7 @ 100 = 700) + service line (3 @ 100 = 300), discount 100, tax 5% on the 1000 subtotal.
2. Post → allocations: stock net 630, service net 270; JE: **Dr Inventory 630, Dr Expense 270, Dr Input VAT 50, Cr AP 950**; balance +7 units at unit cost 90 (630/7).
   - Sanity: Dr 630+270+50 = 950 = Cr. ✓

## Scenario H — Tenant isolation

1. Tenant B calls `GET /api/v1/inventory/products/{sku-001-id}/` → `404` "Product not found." (no disclosure). Same for balances, movements, adjustments, settings, and posting a purchase/sales invoice referencing tenant-A's product → rejected at create/edit.

## Regression & limits

- Backend: `cd backend && py -m pytest apps/ -q` → baseline **223** green + the new inventory suite.
- Migrations clean: `py manage.py makemigrations --check --dry-run` and `py manage.py migrate --check`.
- Frontend: `npm run build` (frontend/); new files lint-clean (16 pre-existing problems only).
- Known limits (documented non-goals): multi-warehouse transfers, batch/lot/serial, expiry, returns/credit notes, manufacturing/BOM, forecasting, FIFO/standard cost, auto-numbering — all deferred.