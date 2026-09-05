# Implementation Tasks: Inventory Management (Feature 012)

Status per task: `[ ]` not started (planning), `[x]` complete (implementation close-out).

## Phase 1 — Foundation: `apps/inventory` app + models + migration `0001_initial`

- [x] Register `apps.inventory` in `INSTALLED_APPS` (`config/settings/base.py`).
- [x] `apps/inventory/apps.py` with `name = "apps.inventory"`; package init present.
- [x] `apps/inventory/admin.py` (optional registration for tenant-scoped models).
- [x] `models.py`: `Product` (tenant, sku unique-per-tenant, name, unit, is_active).
- [x] `models.py`: `Warehouse` (tenant, name unique-per-tenant, is_active).
- [x] `models.py`: `InventorySettings` (inventory_account Asset, cogs_account Expense, adjustments_account Expense, default_warehouse; unique per tenant).
- [x] `models.py`: `StockBalance` (product+warehouse unique, quantity, value, moving_avg_cost).
- [x] `models.py`: `StockMovement` (product, warehouse, movement_type Receipt/Issue/Adjustment, signed quantity, unit_cost, value, optional purchase_invoice / sales_invoice / adjustment FKs; immutable).
- [x] `models.py`: `StockAdjustment` (number unique-per-tenant, status Draft/Posted, adjustment_date, reason, posted_journal OneToOne, posted_at).
- [x] `models.py`: `StockAdjustmentLine` (adjustment CASCADE, product PROTECT, signed quantity != 0).
- [x] `apps/inventory/migrations/0001_initial.py` (all tables + constraints/indexes).
- [x] `InventorySettingsService.get()` — single-row `get_or_create` + lazy atomic creation of default `Warehouse("Default")`.
- [x] `InventorySettingsService.update()` — type-guarded account mapping (Asset/Expense) + tenant-scoped warehouse validation.
- [x] `makemigrations --check --dry-run` clean; `py -m pytest apps/ -q` baseline 223 still green. `StockService` engine (receive/issue/allocate/validate) and `StockAdjustmentService` drafted in `services.py`.

## Phase 2 — Purchases integration (additive)

- [x] `apps/purchases/migrations/0002_add_product_to_purchase_invoiceline.py` (nullable `product` FK, depends on inventory `0001`).
- [x] `PurchaseInvoiceLine.product` FK (PROTECT, `related_name="+"`, null=True, lazy string reference).
- [x] `PurchaseInvoiceSerializer` line payload: additive `product_id` field (tenant-scoped `TenantScopedProductField`).
- [x] `PurchaseInvoiceService.create_draft`/`update_draft`: accept optional `product_id` per line (tenant-scoped validation; draft lines may be changed).
- [x] `PurchaseInvoiceService.post_invoice`: product-aware branch — when any stock line:
  - [x] require inventory settings (`inventory_account` + default warehouse; tenant + active + Asset);
  - [x] proportional discount allocation (`line_net_i = line_subtotal_i − discount × line_subtotal_i / subtotal`);
  - [x] lock `StockBalance` rows ordered `(product_id, warehouse_id)` inside `transaction.atomic()`;
  - [x] create receipt `StockMovement`s and update `StockBalance` (qty + value + moving_avg_cost);
  - [x] build the JE with Dr Inventory (Σ product-line nets) + Dr Expense (Σ service-line nets) + Dr Input VAT + Cr AP.
  - [x] no-product path byte-for-byte Feature 011 (regression).
- [x] Purchases posting tests for the inventory branch (see Phase 5).

## Phase 3 — Sales integration (additive)

- [x] `apps/sales/migrations/0004_add_product_to_sales_invoiceline.py` (nullable `product` FK, depends on inventory `0001`).
- [x] `SalesInvoiceLine.product` FK (PROTECT, `related_name="+"`, null=True, lazy string reference).
- [x] `SalesInvoiceSerializer` line payload: additive `product_id` field (tenant-scoped).
- [x] `SalesInvoiceService.create_draft`/`update_draft`: accept optional `product_id` per line.
- [x] `SalesInvoiceService.post_invoice`: stock branch — when any stock line:
  - [x] require inventory settings (`inventory_account` + `cogs_account`);
  - [x] lock `StockBalance` rows ordered, re-validate negative stock (`out_qty ≤ balance.quantity`);
  - [x] compute COGS = Σ qty × moving_avg_cost; create issue `StockMovement`s; update balances;
  - [x] write the JE with the Dr COGS / Cr Inventory self-balancing pair + existing AR/Revenue/VAT legs.
  - [x] no-product path byte-for-byte Feature 009 (regression).
- [x] Sales posting tests for the stock branch (see Phase 5).

## Phase 4 — Inventory services + API

- [x] `services.py`: `StockService` (receive / issue / adjust primitives; invariant helpers balance == Σ movements).
- [x] `services.py`: `StockAdjustmentService` (create_draft / update_draft / delete_adjustment / post_adjustment).
- [x] `permissions.py`: `CanViewInventory`, `CanManageInventory`, `CanConfigureInventory`.
- [x] Serializers: `ProductSerializer`, `WarehouseSerializer`, `StockBalanceSerializer`, `StockMovementSerializer`, `StockAdjustmentSerializer`, `StockAdjustmentPostSerializer`, `InventorySettingsSerializer` (+ `*_name` fields, additive `product_id` on sales/purchases line serializers).
- [x] Views: `ProductViewSet`, `WarehouseViewSet` (read), `StockBalanceViewSet` (read + filters), `StockAdjustmentViewSet` (+ `post_adjustment`), `InventorySettingsViewSet` (`GET`/`PUT current/`).
- [x] URLs: router entries under `api/v1/inventory/`; include in `config/urls.py`.
- [x] `makemigrations --check --dry-run` clean; full suite regression green.

## Phase 5 — Backend tests (`apps/inventory/tests/`)

- [x] `test_products_api.py`: CRUD, duplicate sku 400, delete-with-use → 400/deactivate, permissions matrix, tenant isolation (404/generic).
- [x] `test_inventory_settings_api.py`: single row, Account type guards, lazy default warehouse, cross-tenant account/warehouse rejection.
- [x] `test_purchase_inventory_api.py`: receipt movement + Dr Inventory/JE split + proportional discount + service-line preservation + settings-missing error + cross-tenant product + no partial state on failure.
- [x] `test_sales_inventory_api.py`: COGS leg + issue movement + negative-stock rejection (no JE) + immutability + weighted-average arithmetic + concurrent-posting serialization.
- [x] `test_adjustments_api.py`: draft→posted, +/− JE legs, negative guard, duplicate number, idempotent post, posted immutability, tenant isolation.
- [x] `test_stock_ledger_tie.py`: quickstart walkthrough — after each step `balance.qty == Σ movements.qty`, `balance.value == Σ movements.value == inventory-account ledger balance`.
- [x] Regression: `py -m pytest apps/ -q` — baseline **223** green + new inventory suite green (274 passed, 1 postgres-only skip).

## Phase 6 — Frontend

- [x] `frontend/src/services/inventoryService.js`.
- [x] `components/Layout/InventoryNav.jsx` (Products / Stock / Adjustments / Settings).
- [x] `pages/inventory/ProductsPage.jsx` + `components/inventory/products/ProductModal.jsx`.
- [x] `pages/inventory/StockPage.jsx` (balances table + movements table; filters).
- [x] `pages/inventory/AdjustmentsPage.jsx` + `components/inventory/adjustments/AdjustmentForm.jsx`.
- [x] `pages/inventory/InventorySettingsPage.jsx` (AccountSelect reuse x3 + warehouse display).
- [x] `components/inventory/ProductSelect.jsx` (searchable product dropdown, additive).
- [x] Wire `ProductSelect` into existing `SalesInvoiceForm` and `PurchaseInvoiceForm` line editors (optional column).
- [x] Routes `/inventory/products|stock|adjustments|settings` in `App.jsx`.
- [x] `npm run build` passes; new files lint-clean (16 pre-existing only).

## Phase 7 — Docs & close-out

- [x] tasks.md all `[x]`; quickstart scenarios verified; report.md written.
- [x] `checklists/requirements.md` items verified `[x]`.
- [x] AGENTS.md → IMPLEMENTATION COMPLETE for `012-inventory`.
- [x] `.specify/feature.json` → `specs/012-inventory`.
- [x] Commit via `.specify/extensions/git/scripts/powershell/auto-commit.ps1`; working tree clean.