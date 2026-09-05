# Implementation Tasks: Inventory Management (Feature 012)

Status per task: `[ ]` not started (planning), `[x]` complete (implementation close-out).

## Phase 1 — Foundation: `apps/inventory` app + models + migration `0001_initial`

- [ ] Register `apps.inventory` in `INSTALLED_APPS` (`config/settings/base.py`).
- [ ] `apps/inventory/apps.py` with `name = "inventory"`; package init present.
- [ ] `apps/inventory/admin.py` (optional registration for tenant-scoped models).
- [ ] `models.py`: `Product` (tenant, sku unique-per-tenant, name, unit, is_active).
- [ ] `models.py`: `Warehouse` (tenant, name unique-per-tenant, is_active).
- [ ] `models.py`: `InventorySettings` (inventory_account Asset, cogs_account Expense, adjustments_account Expense, default_warehouse; unique per tenant).
- [ ] `models.py`: `StockBalance` (product+warehouse unique, quantity, value, moving_avg_cost).
- [ ] `models.py`: `StockMovement` (product, warehouse, movement_type Receipt/Issue/Adjustment, signed quantity, unit_cost, value, optional purchase_invoice / sales_invoice / adjustment FKs; immutable).
- [ ] `models.py`: `StockAdjustment` (number unique-per-tenant, status Draft/Posted, adjustment_date, reason, posted_journal OneToOne, posted_at).
- [ ] `models.py`: `StockAdjustmentLine` (adjustment CASCADE, product PROTECT, signed quantity != 0).
- [ ] `apps/inventory/migrations/0001_initial.py` (all tables + constraints/indexes).
- [ ] `InventorySettingsService.get()` — single-row `get_or_create` + lazy atomic creation of default `Warehouse("Default")`.
- [ ] `InventorySettingsService.update()` — type-guarded account mapping (Asset/Expense) + tenant-scoped warehouse validation.
- [ ] `makemigrations --check --dry-run` clean; `py -m pytest apps/ -q` baseline 223 still green.

## Phase 2 — Purchases integration (additive)

- [ ] `apps/purchases/migrations/0002_add_product_to_purchase_invoiceline.py` (nullable `product` FK, depends on inventory `0001`).
- [ ] `PurchaseInvoiceLine.product` FK (PROTECT, `related_name="+"`, null=True, lazy string reference).
- [ ] `PurchaseInvoiceSerializer` line payload: additive `product_id` field (tenant-scoped `TenantScopedProductField`).
- [ ] `PurchaseInvoiceService.create_draft`/`update_draft`: accept optional `product_id` per line (tenant-scoped validation; draft lines may be changed).
- [ ] `PurchaseInvoiceService.post_invoice`: product-aware branch — when any stock line:
  - [ ] require inventory settings (`inventory_account` + default warehouse; tenant + active + Asset);
  - [ ] proportional discount allocation (`line_net_i = line_subtotal_i − discount × line_subtotal_i / subtotal`);
  - [ ] lock `StockBalance` rows ordered `(product_id, warehouse_id)` inside `transaction.atomic()`;
  - [ ] create receipt `StockMovement`s and update `StockBalance` (qty + value + moving_avg_cost);
  - [ ] build the JE with Dr Inventory (Σ product-line nets) + Dr Expense (Σ service-line nets) + Dr Input VAT + Cr AP.
  - [ ] no-product path byte-for-byte Feature 011 (regression).
- [ ] Purchases posting tests for the inventory branch (see Phase 5).

## Phase 3 — Sales integration (additive)

- [ ] `apps/sales/migrations/0004_add_product_to_sales_invoiceline.py` (nullable `product` FK, depends on inventory `0001`).
- [ ] `SalesInvoiceLine.product` FK (PROTECT, `related_name="+"`, null=True, lazy string reference).
- [ ] `SalesInvoiceSerializer` line payload: additive `product_id` field (tenant-scoped).
- [ ] `SalesInvoiceService.create_draft`/`update_draft`: accept optional `product_id` per line.
- [ ] `SalesInvoiceService.post_invoice`: stock branch — when any stock line:
  - [ ] require inventory settings (`inventory_account` + `cogs_account`);
  - [ ] lock `StockBalance` rows ordered, re-validate negative stock (`out_qty ≤ balance.quantity`);
  - [ ] compute COGS = Σ qty × moving_avg_cost; create issue `StockMovement`s; update balances;
  - [ ] write the JE with the Dr COGS / Cr Inventory self-balancing pair + existing AR/Revenue/VAT legs.
  - [ ] no-product path byte-for-byte Feature 009 (regression).
- [ ] Sales posting tests for the stock branch (see Phase 5).

## Phase 4 — Inventory services + API

- [ ] `services.py`: `StockService` (receive / issue / adjust primitives; invariant helpers balance == Σ movements).
- [ ] `services.py`: `StockAdjustmentService` (create_draft / update_draft / delete_adjustment / post_adjustment).
- [ ] `permissions.py`: `CanViewInventory`, `CanManageInventory`, `CanConfigureInventory`.
- [ ] Serializers: `ProductSerializer`, `WarehouseSerializer`, `StockBalanceSerializer`, `StockMovementSerializer`, `StockAdjustmentSerializer`, `StockAdjustmentPostSerializer`, `InventorySettingsSerializer` (+ `*_name` fields, additive `product_id` on sales/purchases line serializers).
- [ ] Views: `ProductViewSet`, `WarehouseViewSet` (read), `StockBalanceViewSet` (read + filters), `StockAdjustmentViewSet` (+ `post_adjustment`), `InventorySettingsViewSet` (`GET`/`PUT current/`).
- [ ] URLs: router entries under `api/v1/inventory/`; include in `config/urls.py`.
- [ ] `makemigrations --check --dry-run` clean; full suite regression green.

## Phase 5 — Backend tests (`apps/inventory/tests/`)

- [ ] `test_products_api.py`: CRUD, duplicate sku 400, delete-with-use → 400/deactivate, permissions matrix, tenant isolation (404/generic).
- [ ] `test_inventory_settings_api.py`: single row, Account type guards, lazy default warehouse, cross-tenant account/warehouse rejection.
- [ ] `test_purchase_inventory_api.py`: receipt movement + Dr Inventory/JE split + proportional discount + service-line preservation + settings-missing error + cross-tenant product + no partial state on failure.
- [ ] `test_sales_inventory_api.py`: COGS leg + issue movement + negative-stock rejection (no JE) + immutability + weighted-average arithmetic + concurrent-posting serialization.
- [ ] `test_adjustments_api.py`: draft→posted, +/− JE legs, negative guard, duplicate number, idempotent post, posted immutability, tenant isolation.
- [ ] `test_stock_ledger_tie.py`: quickstart walkthrough — after each step `balance.qty == Σ movements.qty`, `balance.value == Σ movements.value == inventory-account ledger balance`.
- [ ] Regression: `py -m pytest apps/ -q` — baseline **223** green + new inventory suite green.

## Phase 6 — Frontend

- [ ] `frontend/src/services/inventoryService.js`.
- [ ] `components/Layout/InventoryNav.jsx` (Products / Stock / Adjustments / Settings).
- [ ] `pages/inventory/ProductsPage.jsx` + `components/inventory/products/ProductModal.jsx`.
- [ ] `pages/inventory/StockPage.jsx` (balances table + movements table; filters).
- [ ] `pages/inventory/AdjustmentsPage.jsx` + `components/inventory/adjustments/AdjustmentForm.jsx`.
- [ ] `pages/inventory/InventorySettingsPage.jsx` (AccountSelect reuse x3 + warehouse display).
- [ ] `components/inventory/ProductSelect.jsx` (searchable product dropdown, additive).
- [ ] Wire `ProductSelect` into existing `SalesInvoiceForm` and `PurchaseInvoiceForm` line editors (optional column).
- [ ] Routes `/inventory/products|stock|adjustments|settings` in `App.jsx`.
- [ ] `npm run build` passes; new files lint-clean (16 pre-existing only).

## Phase 7 — Docs & close-out

- [ ] tasks.md all `[x]`; quickstart scenarios verified; report.md written.
- [ ] `checklists/requirements.md` items verified `[x]`.
- [ ] AGENTS.md → IMPLEMENTATION COMPLETE for `012-inventory`.
- [ ] `.specify/feature.json` → `specs/012-inventory`.
- [ ] Commit via `.specify/extensions/git/scripts/powershell/auto-commit.ps1`; working tree clean.