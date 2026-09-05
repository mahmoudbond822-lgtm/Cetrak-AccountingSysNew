# Feature 012 — Inventory Management: Final Report

Status: IMPLEMENTATION COMPLETE — all backend tests passing (274 passed, 1 postgres-only skip), frontend builds, new files lint-clean.

## Summary

Implemented perpetual inventory integrated directly with the Accounting system: **Purchase → Stock Receipt → Inventory → Sales → Stock Issue → COGS → Accounting**. A new tenant-scoped `apps/inventory` app owns:

- **Product catalog** (`Product`: tenant-unique SKU, name, unit, `is_active`), a single lazy **Default `Warehouse`** per tenant, and one **`InventorySettings`** row (inventory / COGS / adjustments accounts + default warehouse).
- **`StockBalance`** (quantity, value, moving-average cost snapshot) per `(product, warehouse)` backed by an immutable append-only **`StockMovement`** ledger.
- **`StockAdjustment`** drafts that post balanced `ADJ-INV-{number}` journal entries at current weighted-average cost.

Purchase-invoice product lines post a **stock receipt** (Dr Inventory, Dr Input VAT, Cr AP — product-line nets after proportional discount, VAT excluded from cost); sales-invoice product lines post a **stock issue** plus **Dr COGS / Cr Inventory** at the moving weighted-average cost inside the existing balanced `SALES-INV-{number}` entry. Service lines (no `product_id`) keep Features 009/011 behavior byte-for-byte via additive nullable `product` FKs.

Posting is atomic, row-locked (`select_for_update` on `StockBalance` rows in stable `(product_id, warehouse_id)` order), idempotent (status guard + unique `(tenant, reference)`), tenant-isolated, and **negative stock is hard-rejected** — a failed posting leaves zero artifacts.

## Files Changed / Added

### Backend (new — `apps/inventory`)
- `models.py` — `Product` (tenant-unique `sku`, name, unit, `is_active`), `Warehouse` (tenant-unique name, `is_active`), `InventorySettings` (single row per tenant: `inventory_account` Asset, `cogs_account` Expense, `adjustments_account` Expense, `default_warehouse`), `StockBalance` (unique `(product, warehouse)`, quantity, value, `moving_avg_cost` snapshot), `StockMovement` (immutable; `movement_type` Receipt/Issue/Adjustment; signed qty, `unit_cost`, `value`; optional `purchase_invoice` / `sales_invoice` / `adjustment` source FKs), `StockAdjustment` (tenant-unique `number`, Draft/Posted, `posted_journal` OneToOne, `posted_at`) + `StockAdjustmentLine`. All money/qty `Decimal(19,4)`; all stock FKs PROTECT (except adjustment lines CASCADE).
- `migrations/0001_initial.py` — generated (constraints/indexes incl. per-tenant uniques, non-zero signed-quantity check).
- `permissions.py` — `CanViewInventory` (Admin/Accountant/Manager), `CanManageInventory` (Admin/Accountant — products incl. deactivate + adjustments incl. posting), `CanConfigureInventory` (Admin).
- `services.py` — `InventorySettingsService` (single-row get/update, type-guarded accounts, lazy atomic Default-warehouse creation); `StockService` (receive / issue / adjustment primitives + invariant helpers); `StockAdjustmentService` (`create_draft`, `update_draft`, `delete_adjustment`, `post_adjustment`).
- `serializers.py` — `ProductSerializer`, `StockAdjustmentSerializer` (writeable line quantity), `StockAdjustmentPostSerializer`, `InventorySettingsSerializer` (+ `*_name` fields), read-only `WarehouseSerializer` / `StockBalanceSerializer` / `StockMovementSerializer`; tenant-scoped PK fields.
- `views.py` — `ProductViewSet` (atomic create/update so duplicate-SKU `IntegrityError` surfaces as a clean 400), `WarehouseViewSet` (read), `StockBalanceViewSet` (read + filters), `StockMovementViewSet` (read + filters), `StockAdjustmentViewSet` (+ `post_adjustment`), `InventorySettingsViewSet` (`GET/PUT current/`).
- `urls.py` — basenames `product`, `warehouse`, `stock-balance`, `stock-movement`, `stock-adjustment`, `inventory-settings`.
- `tests/base.py` + 6 test files (see Tests below).

### Backend (modified)
- `apps/purchases/models.py` / `serializers.py` / `services.py` — additive nullable `PurchaseInvoiceLine.product` FK + `product_id` line field; purchase posting leg split (Dr Inventory / Dr Expense / Dr Input VAT / Cr AP) with proportional discount allocation; `_resolve_product` accepts a `Product` instance or pk and re-verifies tenant + `is_active`.
- `apps/purchases/migrations/0002_add_product_to_purchase_invoiceline.py` — nullable `product` FK (depends on inventory `0001`).
- `apps/sales/models.py` / `serializers.py` / `services.py` — additive nullable `SalesInvoiceLine.product` FK + `product_id` line field; sales posting adds the self-balancing Dr COGS / Cr Inventory pair.
- `apps/sales/migrations/0004_add_product_to_sales_invoiceline.py` — nullable `product` FK (depends on inventory `0001`).
- `backend/config/settings/base.py` — `apps.inventory` in `INSTALLED_APPS`.
- `backend/config/urls.py` — includes `api/v1/inventory/`.

No changes to `apps/accounting`, `SalesSettings`, `PurchaseSettings`, or payment behavior.

### Frontend (new)
- `src/services/inventoryService.js` — products / warehouses / balances / movements / adjustments / settings actions.
- `src/components/Layout/InventoryNav.jsx` — Products / Stock / Adjustments / Settings (latter admin-only).
- `src/pages/inventory/{ProductsPage,StockPage,AdjustmentsPage,InventorySettingsPage}.jsx`.
- `src/components/inventory/ProductSelect.jsx` (searchable product dropdown, additive) and `src/components/inventory/products/ProductModal.jsx`, `src/components/inventory/adjustments/AdjustmentForm.jsx`.

### Frontend (modified)
- `src/App.jsx` — routes `/inventory/products|stock|adjustments|settings`.
- `src/components/sales/invoices/InvoiceForm.jsx` and `src/components/purchases/invoices/PurchaseInvoiceForm.jsx` — optional product column; sends `product_id: null` for service lines.

### Docs
- `specs/012-inventory/{tasks.md,checklists/requirements.md}` — marked complete.
- `specs/012-inventory/report.md` (this file).
- `AGENTS.md` — phase marker updated to Feature 012 IMPLEMENTATION COMPLETE.

## Migrations

- `apps.inventory.0001_initial` — products, warehouses, inventory settings, stock balances, stock movements, stock adjustments + lines; all per-tenant uniques; PROTECT on all stock FKs.
- `apps.purchases.0002_add_product_to_purchase_invoiceline` — additive nullable `product` FK.
- `apps.sales.0004_add_product_to_sales_invoiceline` — additive nullable `product` FK.
  `makemigrations --check --dry-run` and `migrate --check` both clean.

## API Surface (`api/v1/inventory/`)

| Endpoint | Method | Permission | Notes |
|---|---|---|---|
| `products/` | GET/POST | View/Manage | `?search=`, `?is_active=`; duplicate SKU → 400 |
| `products/{id}/` | GET/PATCH/DELETE | View/Manage/Manage | delete → 400 if referenced, else 204 deactivate |
| `warehouses/` | GET | View | read-only; lazy Default created on settings get |
| `stock-balances/` | GET | View | `?product=`, `?warehouse=` |
| `stock-movements/` | GET | View | `?product=`, `?warehouse=`, `?movement_type=` |
| `adjustments/` | GET/POST | View/Manage | draft with lines |
| `adjustments/{id}/` | GET/PATCH/DELETE | View/Manage/Manage | drafts only for PATCH/DELETE |
| `adjustments/{id}/post_adjustment/` | POST | ManageInventory | balanced `ADJ-INV-{n}` JE |
| `settings/current/` | GET/PUT | View/Configure | get-or-create row + lazy warehouse; type-guarded accounts |

Existing sales/purchases endpoints unchanged; their line payloads gain additive optional `product_id`.

## Accounting Integration

Posting (inside `transaction.atomic()`, `StockBalance` rows locked with `select_for_update` in stable order, idempotent via status guard + unique `(tenant, reference)`):

- **Purchase receipt**: requires settings with same-tenant active Asset `inventory_account` + default warehouse; product-line nets allocated proportionally to discount (`line_net_i = subtotal_i − discount × subtotal_i / subtotal`). JE `reference = "PUR-INV-{n}"`: **Dr Inventory (Σ product-line nets), Dr Expense (Σ service-line nets), Dr Input VAT (tax), Cr AP (total)** — sums to `subtotal − discount + tax`.
- **Sales issue**: requires Asset `inventory_account` + Expense `cogs_account`; COGS = Σ qty × current weighted-average cost; out-qty ≤ balance enforced under the lock. JE `reference = "SALES-INV-{n}"`: existing Dr AR / Cr Revenue / Cr VAT legs **plus** the self-balancing **Dr COGS / Cr Inventory** pair.
- **Adjustment**: at current avg cost, `reference = "ADJ-INV-{number}"`: **Dr Inventory / Cr Adjustments** (gain) or **Dr Adjustments / Cr Inventory** (loss).
- Money stays `Decimal(19,4)` end to end; `value` is the authoritative aggregate and `moving_avg_cost = value / quantity` a display snapshot. Invariant `balance == Σ movements` (qty and value) is asserted at every ledger-tie step.

## Frontend

Inventory UI follows the existing design system (inline styles, shared `Table`/`Modal`/`Button`/`Input`, `AccountSelect`). Invoice forms now show an optional product picker column and send `product_id: null` for service lines, preserving 009/011 payloads. Settings is gated to Admin on the client (server 403 authoritative). Money/qty rendered via `Number(v).toFixed(4)` from backend `"{:.4f}"` strings. `npm run build` passes. Lint: exactly the 16 pre-existing problems remain (15 errors + 1 warning in earlier feature files); the new inventory files add zero lint problems.

## Security

- Every query scoped via `.for_tenant(request.tenant_id)`; cross-tenant lookups return generic 404s/400s (no disclosure).
- Settings and posting re-validate account/product tenant, `is_active`, and account type at post time — defense in depth.
- Permission classes gate the API; a Manager cannot write, adjustments posting rides `CanManageInventory`.
- Safe errors: duplicate-SKU and insufficient-stock failures never disclose other tenants' data; failed postings leave zero journal/movement/balance artifacts.

## Tests

- Full suite: `cd backend && $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/ -q` → **274 passed, 1 skipped** (223 pre-existing baseline + 52 new inventory tests; the single skip is `test_concurrent_posting_serializes`, PostgreSQL-only row-lock serialization).
- New suite (`apps/inventory/tests/`): `test_products_api.py` (14), `test_inventory_settings_api.py` (8), `test_purchase_inventory_api.py` (8), `test_sales_inventory_api.py` (6 passed + 1 postgres-only skip), `test_adjustments_api.py` (14), `test_stock_ledger_tie.py` (1).
- Coverage includes: balanced-JE posting with leg split, proportional discount allocation, weighted-average arithmetic (10 @ 100 / 10 @ 120 → sell 5 → COGS 550), negative-stock hard rejection with zero artifacts, movement immutability, draft→posted adjustments (+/− legs, idempotent post, posted immutability), settings type guards + lazy warehouse, cross-tenant injection, concurrent-posting serialization, permission matrix, and the ledger tie-out `balance == Σ movements == inventory-account ledger balance`.

## Recorded Deviations

1. **No separate `CanPost*` permission** for inventory: stock effects ride the source document's posting permission (`PostPurchaseInvoice` / `PostSalesInvoice`) and adjustments posting rides `CanManageInventory` — documented in the plan/spec.
2. **Single aggregate Inventory leg** on purchase posting (one Dr Inventory line summing all product-line nets), not one Dr line per product line — the JE stays small and balanced; per-line detail lives in `StockMovement`.
3. **Adjustment line quantity** is a writeable `DecimalField(max_digits=19, decimal_places=4)` (signed, `!= 0`), not a read-only method field — drafts must be editable before posting.
4. **Product delete** returns `400` ("Product is referenced by invoice lines / stock and cannot be deleted. Deactivate instead.") when referenced, else `204` deactivate — mirrors the Feature 009/011 customer/vendor rule.
5. **Settings endpoint** uses `GET/PUT current/` (mirrors sales/purchases), per plan.
6. Concurrent-posting serialization is only real on PostgreSQL (`select_for_update`); on the SQLite test DB the test is skipped, all other concurrency/rollback invariants are asserted unskipped.

## Limitations / Follow-ups (deferred, per spec)

- Multi-warehouse transfers (schema already keyed on warehouse; one Default warehouse per tenant now).
- Batch/lot/serial tracking, expiry dating — deferred.
- Returns / credit notes reversing receipts/issues — manual reversing JE is the documented correction path.
- Manufacturing / BOM, forecasting, FIFO or standard costing, auto-numbering — deferred.

## Recommended Next Feature

Feature 013 — Inventory transfers, returns/credit notes, or batch/lot tracking; alternatively AP aging / vendor statements (deferred from Feature 011).