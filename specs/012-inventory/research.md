# Technical Research: Inventory Management (Feature 012)

## Objective

Determine how to introduce stock-keeping (Product catalog, Stock Receipt on purchase posting, Stock Issue + COGS on sales posting, Stock Adjustments) that integrates with the existing Accounting core and the Features 009/010/011 sales + purchases architecture — without breaking any shipped behavior and without over-engineering beyond what the MVP needs.

## 1. Existing Architecture Surveyed

### 1.1 Accounting core (`apps/accounting`)
- `Account` (`TenantScopedModel`): `Type` = Asset/Liability/Equity/Revenue/Expense; `is_active`; parent hierarchy; cash/bank are **Asset**.
- `JournalEntry`: `date`, `description`, `reference` (unique per tenant), `posted`, `posted_at`. `JournalEntryLine`: account FK PROTECT, `debit`/`credit` Decimal(19,4).
- **LedgerService running balance = debit − credit** — reducing an Asset is a **credit**; adding to an Asset is a **debit**.
- `AccountingService.update_account` refuses to change the type of an account that has journal lines; `deactivate_account` refuses accounts with active children or journal lines → the inventory/COGS/adjustments accounts, once used, are protected exactly like the sales/purchases accounts.

### 1.2 Sales domain (`apps/sales`, Features 009 + 010)
- `SalesInvoiceService.post_invoice`: settings guard → `transaction.atomic()` → one balanced JE `SALES-INV-{number}` (Dr AR = total, Cr Revenue = subtotal−discount, Cr VAT when tax>0) → Posted. Idempotent via status guard + `(tenant, reference)` unique.
- `Payment`/`PaymentService` (Feature 010/011, now direction-aware): row-locked atomic posting, unique reference backstop, `IntegrityError → ValueError("Journal entry reference already exists.")`.
- `SalesInvoiceLine`: `description`, `quantity`, `unit_price`, `tax_rate`, computed totals. **No product reference today** — the `product` FK must be *added* (nullable).
- `SalesSettingsService.get()` uses `get_or_create(tenant_id=...)` for a single settings row; `update()` type-guards each account (AR=Asset, revenue=Revenue, vat=Liability).
- Permissions: `CanView*` (Admin/Accountant/Manager), `CanManage*` (Admin/Accountant), `CanPost*` (Admin/Accountant), `CanConfigure*` (Admin).

### 1.3 Purchases domain (`apps/purchases`, Feature 011)
- `PurchaseInvoiceService.post_invoice`: one balanced JE `PUR-INV-{number}` — **Dr Expense** (subtotal−discount), Dr Input VAT (when tax>0, required), Cr AP (total). `PurchaseInvoiceLine` has **no product reference** — `product` FK added, nullable.
- `PurchaseSettingsService.get()` single row; type-guards AP=Liability, expense=Expense, input_vat=Asset.
- General-purpose (non-stock) purchase lines post to **expense** — exactly what inventory-aware posting must *preserve* for service lines so 011 behavior is unchanged when no product is selected.

### 1.4 Shared patterns (the recipes to reuse)
| Concern | Winning pattern (009/010/011) | 012 use |
|---|---|---|
| Posting | `transaction.atomic()` + `select_for_update()` on the affected row(s) + unique `(tenant, reference)` backstop | stock-affecting postings lock `StockBalance` rows |
| Money | `Decimal(19,4)` only, `compute_line_totals` reused, no float | qty/value/unit-cost all Decimal(19,4) |
| Settings | single-row `get_or_create` + type-guarded account FKs | `InventorySettings` (+ default warehouse) |
| Tenant isolation | `.for_tenant()` everywhere; tenant-scoped serializer fields; generic 404s | identical |
| Permissions | per-domain `CanView/CanManage/CanPost/CanConfigure` on existing roles | inventory analogues (no `CanPost*` — see D14) |
| Lifecycle | Draft → Posted → immutable, idempotent | products CRUD; adjustments Draft→Posted |

### 1.5 Deferred-by-brief comparison
The brief explicitly forbids manufacturing/BOM, batch/serial, expiry, advanced transfers, and forecasting "unless research proves necessary". Research does **not** prove any of them necessary for the MVP: the target flow (Purchase → Stock Receipt → Inventory → Sales → Stock Issue → COGS) is fully satisfiable with one product catalog, one default warehouse per tenant, and moving-weighted-average valuation. Transfers and batch tracking are therefore deferred *as data-model features*, but the schema is chosen so adding them later is purely additive (see Q4/Q16).

## 2. The Twenty Research Questions (answered)

| # | Question | Answer | Decision |
|---|---|---|---|
| Q1 | Product vs Item: one catalog entity? | One catalog entity named **Product** (`sku`, `name`, `unit`, `is_active`). No separate Item type in MVP — "Item" in the brief is the same buy/sell unit. | D2 |
| Q2 | SKU/code strategy | Required `sku` Char(50), stripped, **unique per tenant** — exactly the `customer.code`/`vendor.code` pattern. No auto-generation in MVP (user-supplied, mirrors numbering elsewhere). | D2 |
| Q3 | UOM strategy | Free-text `unit` on Product (`pcs`, `kg`, …). A UOM dimension/table with conversions is over-engineering now; unit conversions deferred (documented future work). | D2 |
| Q4 | Warehouse model | Implement a lightweight `Warehouse` (tenant, name, is_active) **plus a lazily-created default** row per tenant. Balances are keyed `(product, warehouse)` so per-warehouse stock already exists. | D3 |
| Q5 | Stock balance model | Maintained `StockBalance` (product, warehouse, `quantity`, `value`, `moving_avg_cost`) as the fast read/fast lock model, updated transactionally. Not rebuilt from movements on every read. | D4 |
| Q6 | Stock movement ledger | **Immutable append-only `StockMovement`** (type, signed qty, unit_cost, value, source FK). No update/delete API; corrections happen via reversing adjustments. | D4 |
| Q7 | Valuation method | **Moving weighted average** per (product, warehouse): receipts raise the average, issues consume the current one. FIFO rejected for MVP (needs per-lot cost layers + lot-consumption bookkeeping), LIFO rejected (rare, nonstandard, not asked), standard cost rejected (needs variance machinery). FIFO documented as future work. | D11 |
| Q8 | Negative stock policy | **Hard reject** — sales issues and negative adjustments must never take a balance below zero; enforced under row lock at posting (atomic with the JE). Backorder/negative-stock allowance deferred (a settings toggle documented as future work). | D10 |
| Q9 | Adjustment policy | `StockAdjustment` `Draft → Posted` (number, date, reason, signed line quantities). Posting → movements + one balanced `ADJ-INV-{n}` JE at current weighted-average cost. Included in MVP because inventory is a real Asset and any count fix must reconcile to the ledger. | D12/D13 |
| Q10 | Purchase integration | Product lines post a **receipt** movement and Dr **Inventory** (net after proportional discount); service lines keep Dr **Expense**. Posting stays a single balanced JE. | D7 |
| Q11 | Sales integration | Product lines post an **issue** movement and Dr **COGS / Cr Inventory** at weighted-average cost on the same JE as AR/Revenue/VAT; service lines stay revenue-only. | D8 |
| Q12 | COGS timing | COGS recognized **at sales-invoice posting** (the stock-issue moment). Periodic/month-end COGS rejected — the brief's flow is a perpetual inventory system. | D9 |
| Q13 | Account mapping | `InventorySettings`: `inventory_account` (Asset), `cogs_account` (Expense), `adjustments_account` (Expense), `default_warehouse`. Mirrors the sales/purchases single-row settings pattern; type-guarded. | D12 |
| Q14 | VAT treatment | Purchase tax legs stay reclaimable **asset** lines (Dr Input VAT) and are **excluded** from capitalized cost; sales output VAT unchanged. No new tax machinery. | D10_D7 |
| Q15 | Sales returns / credit notes | **Deferred** — not part of the brief's flow; the correction path is a reversing `StockAdjustment` + manual reversing JE (same stance as 010/011 cancellation/void). | D16 |
| Q16 | Multi-warehouse | Warehouse entity + per-warehouse balances in MVP; **transfers deferred**. Adding transfers later is additive (a new movement type). | D16 |
| Q17 | Batch/lot/serial | **Deferred** — no lot tables; weighted-average cost makes batch attribution moot. Documented future work (needs new models). | D16 |
| Q18 | Expiry | **Deferred** — no expiry fields anywhere in MVP (retail/non-perishable assumption documented). | D16 |
| Q19 | Concurrency | `transaction.atomic()` + `select_for_update()` on `StockBalance` rows **ordered by (product_id, warehouse_id)** to avoid deadlocks; idempotency via status guards + unique `(tenant, reference)`; negative-stock and COGS checks are re-validated inside the lock. | D13 |
| Q20 | Auditability | Append-only movements + existing immutable posted JEs + balance-invariant tests (`balance.qty == Σ movement.qty`, `balance.value == Σ movement.value`); movement source FKs tie every stock change to a document (JE+invoice/adjustment). | D4 |

## 3. Design Decisions

### D1 — Where does the inventory domain live?
New app **`apps/inventory`** — must be added to `INSTALLED_APPS` in `config/settings/base.py` (unlike `apps.purchases`, which was pre-scaffolded). Tables `inventory_product`, `inventory_warehouse`, `inventory_settings`, `inventory_stockbalance`, `inventory_stockmovement`, `inventory_adjustment`, `inventory_adjustmentline`. Sibling to sales/purchases; no changes to `apps/accounting`.

### D2 — One `Product` catalog entity
No Product/Item split, no item variants/attributes, no default-price fields in MVP. `Product = (sku, name, unit, is_active)` plus tenant inheritance. Product references are *additive nullable FKs* on `PurchaseInvoiceLine` and `SalesInvoiceLine`, so drafts without a product behave byte-for-byte as Features 011/009.

### D3 — `Warehouse` + lazily-created default
Why keep a warehouse entity at all when transfers are deferred? (a) the brief's rapid next milestone after this feature is worth planning for, (b) per-warehouse balances are needed as soon as the second warehouse exists, and (c) migrating balances later is painful. A `Warehouse` table plus a `default_warehouse` setting and `get_or_create`-style lazy "Default" row keeps today's model one-warehouse-simple while making multi-warehouse a purely additive change (a new `Transfer` movement type).

### D4 — Immutable `StockMovement` ledger + maintained `StockBalance`
- `StockMovement`: immutably records every change (type, signed qty, unit_cost, value, source doc FK). Never updated/deleted via any API; the only way to "undo" is a reversing adjustment.
- `StockBalance`: `(product, warehouse)` unique, holds `quantity` and `value` (authoritative) and a `moving_avg_cost` display snapshot. Updated in the same transaction as the movement. Tests assert the invariant `balance == Σ movements` after every posting sequence.

### D5 — Purchase posting leg split (with proportional discount)
Current DR side = `subtotal − discount` (a single expense leg). With inventory:
- Each product line's capitalized net = `line_subtotal − discount × line_subtotal/subtotal` (proportional allocation; legitimate because `discount ≤ subtotal`). Unit cost = that net / `quantity`.
- Service lines (no product) keep the same allocation but post to **expense**.
- JE: Dr Inventory (Σ product-line nets), Dr Expense (Σ service-line nets), Dr Input VAT (tax), Cr AP (total). Sum of Dr legs = `(subtotal − discount) + tax = total` → balanced by construction.
- Input VAT is **not** part of cost (Q14). Line `tax_rate` continues to feed the existing tax math only.
- If there are product lines, posting **requires** `inventory_account` + a default warehouse (tenant + active + Asset). Service-only purchase invoices require nothing new (Feature 011 unchanged).

### D6 — Sales posting COGS leg (self-balancing pair)
JE is currently Dr AR total / Cr Revenue (net) / Cr VAT (when tax>0) — balanced. Adding a stock issue adds **Dr COGS / Cr Inventory for the same total**, which nets to zero, so the JE stays balanced for any mix of product and service lines. COGS per product line = `quantity × balance.moving_avg_cost` (read under the row lock). Stock lines require `cogs_account` + `inventory_account`; a pure-service sales invoice requires nothing new (Feature 009 unchanged).

### D7 — Negative stock & the failure semantics
At posting time (inside the transaction, after `select_for_update`), every product-line issue is checked: `balance.quantity ≥ line.quantity`, else `ValueError("Insufficient stock.")` — no JE, no movement, full rollback. Same guard on adjustments that decrease stock. This is authoritative — the serializer can pre-check, the service enforces.

### D8 — Adjustments (Draft → Posted)
`StockAdjustment(number, adjustment_date, reason, status)` + signed `lines(product, quantity)`. Posting (with `CanManageInventory`):
1. lock each product's `StockBalance` row (ordered);
2. validate settings `adjustments_account` (+ inventory account) and negative-stock guards;
3. create one balanced JE `ADJ-INV-{number}`: for each line, Dr/ Cr Inventory = `|qty| × moving_avg_cost` against Cr/ Dr `adjustments_account`;
4. create movement(s); update balance(s); mark Posted.

### D9 — Settings
`InventorySettings` single row per tenant: `inventory_account` (Asset), `cogs_account` (Expense), `adjustments_account` (Expense), `default_warehouse` (Warehouse FK). `InventorySettingsService.get_or_create` + type-guarded `update` (mirror of sales/purchases settings). Default warehouse is created lazily via the settings service, not by an explicit UI step.

### D10 — Permissions
New `apps/inventory/permissions.py`: `CanViewInventory` (Admin/Accountant/Manager), `CanManageInventory` (Admin/Accountant) — covers product CRUD *and* posting adjustments, `CanConfigureInventory` (Admin). **Deliberate deviation**: no separate `CanPost*` inventory permission — stock postings always ride the source document's posting permission (purchases `CanPostPurchaseInvoice`, sales `CanPostSalesInvoice`), and adjustment posting is a manage action, so a third posting permission adds ceremony without control.

### D11 — Concurrency design
- One concurrency unit = one `StockBalance` row (product × warehouse). All stock changes lock these rows, ordered by `(product_id, warehouse_id)` to make lock acquisition a deadlock-free total order.
- COGS/negative-stock checks and avg-cost computations happen **after** acquiring the lock — so two concurrent sales posts of the same last-5 units serialize correctly.
- JE idempotency: reference uniqueness (`SALES-INV-…`, `PUR-INV-…` already exist; `ADJ-INV-{n}` new) remains the backstop against double-post; `IntegrityError → ValueError`.

### D12 — Errors (no disclosure)
Same wording family: `"Product not found."`, `"Insufficient stock."`, `"Inventory accounting settings are not configured."`, `"Account must be of type …,",` `"Warehouse not found."`, `"SKU already exists."`, `"Adjustment number already exists."`, `"Journal entry reference already exists."`. Tests assert stable substrings.

## 4. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Breaking Feature 009/011 by touching sales/purchases models | The `product` FK is **additive + nullable**; both posting paths keep their existing behavior when no line selects a product; existing tests re-run as the regression gate (223 must stay green). |
| Unbalanced JE when mixing stock + service + discount | Proportional discount allocation is provably sum-preserving (`Σ line_nets = subtotal − discount`); validated by the mixed-invoice test + the sanity check in plan.md. |
| Avg-cost drift / rounding | `value` (Σ of Decimal movement values) is authoritative; `moving_avg_cost` is a display snapshot = `value/quantity`, recomputed per movement. Invariant tests compare balance vs Σ movements. |
| Concurrent issues of the last units | Row-lock `StockBalance` (ordered) + re-validate inside the lock; loser fails with `"Insufficient stock."` and rolls back wholly. |
| Double booking (JP posting + movement) | Both live in the same `transaction.atomic()`; JE reference uniqueness is the idempotency backstop; movement creation is keyed to the same posted document. |
| Inventory account drift vs ledger | Adjustment/sales/purchase posting always pair a movement with a balanced JE so `Σ inventory-account activity == balance.value` (asserted in quickstart). |
| Lazy default-warehouse races (two concurrent first posts) | Settings `get_or_create` + the (tenant) unique constraint make creation idempotent; warehouse creation enclosed in an atomic block. |
| Cross-tenant leakage through product FKs or account mappings | `.for_tenant()` everywhere; tenant-scoped serializer fields (mirror of `TenantScopedAccountField`); generic errors; P0 isolation test matrix. |
| UI/lint regressions in existing purchase/sales forms | Product selector is an *optional additive column*; promise-chained fetch style preserved so new files stay lint-clean (16 pre-existing issues only). |
| Over-engineering (transfers, batches, expiry, BOM, forecasting) | Explicitly deferred (Q15–Q18); `StockMovement.movement_type` + source FK make later types additive. |

## 5. Non-Goals (explicitly out of scope for v1)

- Multi-warehouse transfers, batch/lot/serial, expiry, manufacturing/BOM, forecasting.
- FIFO/LIFO/standard-cost valuation; periodic (month-end) COGS.
- Sales returns / credit notes / purchase returns; automatic number sequences.
- Product default buy/sell prices, price lists, variants/attributes, units conversion, kits/bundles.
- Low-stock alerts/thresholds, reorder points, stock valuation reports dashboard.
- Any change to `apps/accounting` schema, `SalesSettings`, `PurchaseSettings`, payment behavior, or existing roles.
- Editing/deleting posted movements or adjustments (correction = reversing adjustment/manual JE).

## 6. Test Strategy Sketch (mirror sales/purchases layout in `apps/inventory/tests/`)

1. **Products** (`test_products_api.py`): CRUD, duplicate sku, delete-with-use → 400/deactivate, permissions matrix, tenant isolation.
2. **Settings** (`test_inventory_settings_api.py`): single row, type guards (Asset/Expense), warehouse validation, default-warehouse lazy creation.
3. **Purchase integration** (`test_purchase_inventory_api.py`): stock receipt on posting (movement + balance + avg), Dr Inventory leg, proportional discount split, service-line preservation, settings-required error, cross-tenant product, no partial state.
4. **Sales integration** (`test_sales_inventory_api.py`): COGS leg on posting, insufficient-stock rejection (no JE), immutability, weighted-average arithmetic, negative-stock concurrency (two concurrent postings).
5. **Adjustments** (`test_adjustments_api.py`): draft→posted, +/− JEs, negative guard, duplicate number, idempotent posting, tenant isolation.
6. **Ledger tie-out** (`test_stock_ledger_tie.py`): the quickstart walkthrough asserts balance == Σ movements == inventory-account ledger balance after each step.
7. **Regression**: full `apps/` suite — 223 must stay green.

## 7. Definition of Done

1. Three clean additive migrations: `inventory 0001_initial`, `purchases 0002_add_product_to_purchase_invoiceline`, `sales 0004_add_product_to_sales_invoiceline`; `makemigrations --check --dry-run` clean.
2. Product CRUD + uniqueness + tenant isolation green.
3. Purchase posting with product lines: one receipt movement + one balanced JE (Dr Inventory/Dr Input VAT/Cr AP) with proportional discount; service-only posting identical to Feature 011.
4. Sales posting with product lines: one issue movement + one balanced JE with Dr COGS/Cr Inventory at weighted-average cost; insufficient stock leaves zero artifacts.
5. Adjustment posting: balanced `ADJ-INV-{n}` JE + movements; ledger ties to `StockBalance.value`.
6. Cross-tenant products/balances/movements/settings/adjustments denied with generic errors.
7. Full backend suite green (223 baseline + new inventory tests).
8. Frontend build green; new files lint-clean (16 pre-existing only); product selector additive on existing forms.
9. Spec artifacts complete, committed, AGENTS.md updated.