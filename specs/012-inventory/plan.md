# Implementation Plan: Inventory Management (Feature 012)

## Goal

Introduce perpetual stock-keeping — **Product catalog → Stock Balance/Ledger → Purchase-posting Stock Receipt → Sales-posting Stock Issue + COGS → Stock Adjustments → Accounting** — on top of the Features 009/010/011 accounting, sales, and purchases domains. A new `apps/inventory` app owns the catalog, balances, movements, adjustments, and settings; the existing `PurchaseInvoiceService`/`SalesInvoiceService` posting paths gain an optional product-aware branch (stock leg + movements + balance update) while every non-product path stays byte-for-byte unchanged. Valuation is moving weighted average per (product, warehouse), all money is `Decimal(19,4)`, posting is atomic, row-locked, idempotent, and tenant-isolated.

## Constraints (from spec + Constitution)

- Money = `Decimal(19,4)`; **no `float`** in any money path; reuse `sales.services.compute_line_totals`.
- `transaction.atomic()` around every posting; `select_for_update()` on all affected `StockBalance` rows (ordered `(product_id, warehouse_id)`); unique `(tenant, reference)` as the idempotency backstop.
- Tenant isolation on every read via `.for_tenant(request.tenant_id)`; generic errors on cross-tenant references (no disclosure).
- **No changes** to `apps/accounting` schema, `SalesSettings`, `PurchaseSettings`, or payment behavior. Feature 009/010/011 must remain passing unchanged (223-test gate).
- Product FKs on invoice lines are **additive and nullable** — lines without a product post exactly as before.
- No hard-coded account/tenant/warehouse IDs. New accounts all come from tenant settings.
- No new roles; inventory permissions mirror the existing sets. No new frontend dependencies.
- `apps/inventory` must be added to `INSTALLED_APPS`.

## Key design decisions (locked)

| # | Decision |
|---|---|
| D1 | New `apps/inventory` app (fresh, registered in `INSTALLED_APPS`) |
| D2 | One `Product` catalog entity: `sku` unique per tenant, `name`, `unit`, `is_active` |
| D3 | `Warehouse` entity + lazy auto-created default per tenant; per-warehouse balances; transfers deferred |
| D4 | Immutable append-only `StockMovement` ledger + maintained `StockBalance` (qty, value, moving_avg_cost); `balance == Σ movements` invariant |
| D5 | **Moving weighted average** valuation per (product, warehouse); value is authoritative, avg is a snapshot |
| D6 | Negative stock **hard-rejected** at posting (row-locked, atomic, no JE/movement on failure) |
| D7 | Purchase posting: stock lines **Dr Inventory** (net after proportional discount), service lines **Dr Expense**, movements + balance update; VAT excluded from cost |
| D8 | Sales posting: stock lines **Dr COGS / Cr Inventory** at weighted average (self-balancing pair on the existing JE) + issue movement |
| D9 | COGS at **invoice posting** (perpetual); periodic COGS rejected |
| D10 | Adjustments `Draft → Posted`; signed line quantities; movement(s) + balanced JE `ADJ-INV-{n}` |
| D11 | `InventorySettings` single row: `inventory_account` (Asset), `cogs_account` (Expense), `adjustments_account` (Expense), `default_warehouse` |
| D12 | Permissions: `CanViewInventory`, `CanManageInventory` (products + adjustments incl. posting), `CanConfigureInventory`; no separate `CanPost*` (stock postings ride source-document permissions — documented deviation) |
| D13 | APIs at `api/v1/inventory/` (products, warehouses, stock balances read, movements read, adjustments + `post_adjustment`, `settings/current`); purchases/sales urls unchanged |
| D14 | Migrations: `inventory 0001`, `purchases 0002` (nullable product FK), `sales 0004` (nullable product FK); all additive |

## Phases

### Phase 1 — Foundation: `apps/inventory` app + models + migration `0001_initial`
- Register `apps.inventory` in `INSTALLED_APPS`; `apps.py` (name `inventory`), `admin.py` (optional), package init.
- `models.py`: `Product`, `Warehouse`, `InventorySettings`, `StockBalance`, `StockMovement`, `StockAdjustment`, `StockAdjustmentLine` per data-model.md.
- `migrations/0001_initial.py` + settings service (`InventorySettingsService.get_or_create`, type-guarded `update`, lazy default-warehouse creation).
- `makemigrations --check --dry-run` clean.

### Phase 2 — Purchases integration (additive)
- `apps/purchases/migrations/0002_add_product_to_purchase_invoiceline.py`.
- `PurchaseInvoiceLine.product` FK (nullable); `PurchaseInvoiceSerializer` line payload gains additive `product_id` (tenant-scoped field).
- `PurchaseInvoiceService`: draft create/update accept optional `product_id` per line; `post_invoice` gains a product-aware branch (Dr Inventory leg + receipt movements + balance updates inside the existing transaction, proportional discount allocation, settings guard when any stock line). No-product path untouched.
- Permissions unchanged (posting rides `CanPostPurchaseInvoice`).

### Phase 3 — Sales integration (additive)
- `apps/sales/migrations/0004_add_product_to_sales_invoiceline.py`.
- `SalesInvoiceLine.product` FK (nullable); `SalesInvoiceSerializer` line payload gains additive `product_id` (tenant-scoped field).
- `SalesInvoiceService`: draft create/update accept optional `product_id` per line; `post_invoice` gains the stock branch (row-lock `StockBalance`, negative-stock guard, Dr COGS/Cr Inventory leg, issue movements). No-product path untouched.

### Phase 4 — Inventory services + API
- `services.py`: `InventorySettingsService` (Phase 1), `StockService` (`receive`, `issue`, `adjust`, balance/movement reads, invariant helpers), `StockAdjustmentService` (`create_draft`/`update_draft`/`delete_adjustment`/`post_adjustment`).
- `permissions.py`: `CanViewInventory`, `CanManageInventory`, `CanConfigureInventory`.
- Serializers: `ProductSerializer`, `WarehouseSerializer`, `StockBalanceSerializer` (product/warehouse/qty/avg/value + product/warehouse names), `StockMovementSerializer`, `StockBalanceListSerializer` (read), `StockAdjustmentSerializer` (+ signed line serializer), `StockAdjustmentPostSerializer`, `InventorySettingsSerializer` (AccountSelect-friendly `*_name` fields).
- Views/URLs: `ProductViewSet`, `WarehouseViewSet` (read), `StockBalanceViewSet` (read, filters product/warehouse/movement_type), `StockAdjustmentViewSet` (+ `post_adjustment`), `InventorySettingsViewSet` (`GET`/`PUT current/`). Register `/api/v1/inventory/` in `config/urls.py`.

### Phase 5 — Backend tests (`apps/inventory/tests/`) + regression
- `test_products_api.py`, `test_inventory_settings_api.py`, `test_purchase_inventory_api.py`, `test_sales_inventory_api.py`, `test_adjustments_api.py`, `test_stock_ledger_tie.py` (quickstart walkthrough asserts balance == Σ movements == inventory ledger).
- Regression: full `apps/` suite green — baseline **223** must stay green, then grows by the new suite.

### Phase 6 — Frontend
- `frontend/src/services/inventoryService.js`.
- `InventoryNav.jsx` (Products / Stock / Adjustments / Settings) in `components/Layout/`.
- Pages/components: `ProductsPage` + `products/ProductModal`; `StockPage` (balances + movements tables); `AdjustmentsPage` + `adjustments/AdjustmentForm`; `InventorySettingsPage` (AccountSelect reuse).
- **Additive product selector on line forms**: `ProductSelect` component; wire into existing `SalesInvoiceForm` and `PurchaseInvoiceForm` line editors (optional field).
- Routes `/inventory/products|stock|adjustments|settings` in `App.jsx`.
- `npm run build` passes; new files lint-clean (16 pre-existing only).

### Phase 7 — Docs & close-out
- tasks.md `[x]`, report.md, checklists, AGENTS.md → IMPLEMENTATION COMPLETE; commit via `auto-commit.ps1`.

## Sanity check: JE balance (the walking example from the brief)

State after receipts 10 @ 100 then 10 @ 120 (avg 110, value 2200, qty 20).

- **Purchase 1** (10 @ 100, 5% VAT): Dr Inventory 1000, Dr Input VAT 50, Cr AP 1050 → balanced; qty 10, value 1000, avg 100.
- **Purchase 2** (10 @ 120): Dr Inventory 1200, Dr Input VAT 60, Cr AP 1260 → balanced; qty 20, value 2200, avg 110.
- **Sale** (5 @ 150, 5% VAT, COGS 5 × 110 = 550): Dr AR 787.50, Cr Revenue 750.00, Cr VAT 37.50, Dr COGS 550, Cr Inventory 550 → balanced; qty 15, value 1650, avg 110.
- **Adjustment +2**: Dr Inventory 220, Cr Adjustments 220 → balanced; qty 17, value 1870.
- **Adjustment −3**: Dr Adjustments 330, Cr Inventory 330 → balanced; qty 14, value 1540.
- **Ledger tie**: inventory account = +1000 +1200 −550 +220 −330 = **1540 = balance.value**. ✓

Mixed stock/service with discount: stock line net 700, service line net 300, discount 100 → nets 630 + 270; Dr Inventory 630, Dr Expense 270, Dr Input VAT (if tax>0), Cr AP = 900 + tax. Dr sum = 900 + tax = Cr. ✓

## Risks

See research §4 in full. Highest-risk items: (1) modifying the proven 009/011 posting paths — mitigated by additive nullable FKs + the 223-test regression gate + mixed-line tests; (2) discount/avg-cost arithmetic drift — mitigated by proportional allocation (provably sum-preserving) and the `value == Σ movements` invariant tests; (3) concurrency on the last units — mitigated by ordered `select_for_update` on `StockBalance` rows with in-lock re-validation; (4) explicit non-goals (transfers/batches/expiry/BOM/forecasting) kept out per the brief.

## Definition of Done

1. `makemigrations --check --dry-run` clean after all three additive migrations.
2. Product CRUD + sku uniqueness + tenant isolation green; used-product delete → deactivate.
3. Weighted-average walkthrough (10 @ 100, 10 @ 120, sell 5) yields avg 110 / COGS 550 / qty 15 / value 1650 with balanced JEs at every step.
4. Purchase posting with product lines: one balanced JE with Dr Inventory leg + one receipt movement per line + correct balance; service-only invoices post byte-for-byte as Feature 011.
5. Sales posting with product lines: one balanced JE with Dr COGS/Cr Inventory + issue movements; insufficient stock rejected with zero artifacts; service-only invoices post byte-for-byte as Feature 009.
6. Adjustment posting (+2/−3) produces balanced `ADJ-INV-{n}` JEs + movements; ledger ties to `StockBalance.value`; posted adjustments immutable and idempotent.
7. Cross-tenant product/balance/movement/adjustment/settings denied with generic errors.
8. Full backend suite green (223 baseline + new inventory tests).
9. Frontend build green; new files lint-clean (16 pre-existing only); product selector additive on existing forms.
10. Spec artifacts complete, committed, AGENTS.md updated.