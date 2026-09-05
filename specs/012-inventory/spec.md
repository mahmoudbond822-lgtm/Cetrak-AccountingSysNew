# Feature Specification: Inventory Management

**Feature Branch**: `012-inventory`

**Created**: 2026-09-05

**Status**: Draft (awaiting review)

**Input**: User description: "Inventory Management (Feature 012) — Purchase → Stock Receipt → Inventory → Sales → Stock Issue → COGS → Accounting. Requirements: integrate with the existing Accounting system; product/item catalog with stock tracking; quantities; choose the valuation method (moving weighted average or FIFO); VAT support; purchases integration (stock receipt, Dr Inventory on posting); sales integration (Dr COGS / Cr Inventory at posting); stock adjustments; receipts/shipments; tenant isolation; no advanced features (no manufacturing/BOM, batch/serial, expiry, advanced transfers, forecasting) unless research proves them necessary."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage the product catalog (Priority: P1)

An accountant manages a tenant-scoped product catalog. Each **Product** has `sku` (unique per tenant), `name`, `unit` (UOM), and `is_active`. Products are the units of stock that purchase and sales invoice lines can reference; a product that has been used cannot be hard-deleted (deactivate instead).

**Why this priority**: A product catalog is the foundation of every downstream feature — no stock receipt or issue can exist without a product.

**Independent Test**: Can be fully tested by creating a product, editing it, attempting a duplicate `sku`, attempting to delete a used product, and attempting tenant-B access to a tenant-A product.

**Acceptance Scenarios**:

1. **Given** an Admin/Accountant role, **When** a product is created with `sku`, `name`, `unit`, **Then** it is stored and returned with `is_active=true`, and a second product with the same tenant/`sku` is rejected.
2. **Given** a product referenced by purchase or sales lines, **When** delete is attempted, **Then** the system rejects it and forbids hard deletion; an unused product is deactivated (`is_active=false`). This mirrors the customer/vendor behavior.
3. **Given** tenant B, **When** tenant A's product id is requested, **Then** `404` with a generic error (no disclosure).

---

### User Story 2 - Purchase posting creates a stock receipt (Priority: P1)

A purchase invoice containing product lines posts a stock receipt **and** the accounting entry: each stock line increases the product's on-hand balance and capitalizes its net cost, **Dr Inventory** (and **Dr Input VAT**, **Cr AP**) instead of the Feature 011 single expense leg. Grab-bag/service lines (no product) keep posting **Dr Expense** exactly as today.

**Why this priority**: This is the purchases→inventory link from the feature description — inventory value originates here.

**Independent Test**: Can be fully tested by posting the 10,000 + 1,500 VAT purchase from Feature 011 against a product and verifying balance `qty=10`, the single balanced JE (Dr Inventory 10,000, Dr Input VAT 1,500, Cr AP 11,500), and a receipt `StockMovement`.

**Acceptance Scenarios**:

1. **Given** an inventory-aware purchase invoice (`product` on each line, net 10,000, VAT 1,500), **When** it is posted, **Then** one balanced Journal Entry is created — Dr Inventory 10,000, Dr Input VAT 1,500, Cr Accounts Payable 11,500 — the stock balance becomes `qty 10 / value 10,000`, and exactly one receipt movement exists.
2. **Given** a purchase invoice with a mix of product lines and service lines (no product), **When** posted, **Then** the Debit side splits: product lines → Dr Inventory (net after proportional discount), service lines → Dr Expense, and the JE still balances to Cr AP = total.
3. **Given** a product line purchase invoice but **no inventory settings** (inventory account / default warehouse), **When** posting is attempted, **Then** it fails with a configuration error and no Journal Entry or movement is created.
4. **Given** a purchase invoice without product references (Feature 011 behavior), **When** posted, **Then** posting is byte-for-byte the Feature 011 behaviour (Dr Expense, no movements), so the 223-test regression stays green.

---

### User Story 3 - Sales posting issues stock and books COGS (Priority: P1)

A sales invoice containing product lines posts a stock issue **and** the COGS entry: each stock line decreases on-hand balance and, at its **weighted-average cost**, books **Dr COGS / Cr Inventory** inside the same balanced Journal Entry as the existing **Dr AR / Cr Revenue / Cr VAT**.

**Why this priority**: This is the sales→COGS link — the point of inventory-tracking product valuation through to the profit & loss.

**Independent Test**: Can be fully tested with the valuation sequence 10 @ 100 then 10 @ 120 (weighted average 110), then selling 5 @ 150 — verifying one balanced JE with Dr AR 787.50, Cr Revenue 750.00, Cr VAT 37.50, Dr COGS 550.00, Cr Inventory 550.00, balance `qty 15 / value 1,650`.

**Acceptance Scenarios**:

1. **Given** a sold product, **When** its sales invoice is posted, **Then** one balanced JE books **Dr COGS = qty × weighted-average unit cost** and **Cr Inventory** the same amount, on the same entry that books Dr AR/Cr Revenue/Cr VAT, and the stock balance decreases accordingly.
2. **Given** a product line with insufficient stock, **When** posting is attempted, **Then** it fails ("Insufficient stock.") and **no** Journal Entry or movement is created.
3. **Given** a sales invoice without product references (Feature 009 behavior), **When** posted, **Then** posting is unchanged (no COGS leg, no movements), and the 223-test regression stays green.
4. **Given** a posted sales invoice, **When** edit is attempted, **Then** it is rejected (immutable after posting, as today).

---

### User Story 4 - Weighted-average valuation stays correct across movements (Priority: P1)

On-hand value and moving-weighted-average cost are maintained per product+warehouse on every receipt/issue. A receipt updates the average: `new_avg = (qty × avg + in_qty × in_unit_cost) / (qty + in_qty)`; an issue consumes the current average. All money flows are `Decimal(19,4)`.

**Why this priority**: The valuation method is a core design decision; this story proves the arithmetic end-to-end.

**Independent Test**: Can be fully tested by the 10 @ 100 + 10 @ 120 → sell 5 sequence and checking `COGS = 550.0000`, `balance value = 1,650.0000`, `avg = 110.0000` after the sale.

**Acceptance Scenarios**:

1. **Given** receipts 10 @ 100 then 10 @ 120, **When** the balance is read, **Then** `quantity = 20`, `value = 2200.0000`, `moving_avg_cost = 110.0000`.
2. **Given** that state, **When** 5 units are sold and the invoice posted, **Then** `COGS = 550.0000`, balance `quantity = 15`, `value = 1650.0000`, `moving_avg_cost = 110.0000`.
3. **Given** `moving_avg_cost`, **When** the value is rounded at movement time, **Then** the stored `value` (the authoritative aggregate) never drifts from `Σ movement values` — the invariant `balance.value == Σ movements.value` is asserted in tests.

---

### User Story 5 - Stock adjustments (Priority: P2)

An accountant records a draft **Stock Adjustment** (number, date, reason, signed quantity per line) and posts it. Posting creates movement(s) and one balanced Journal Entry **Dr/Cr Inventory** against **Cr/Dr Adjustments** at the current weighted-average cost; a negative quantity can never take stock below zero.

**Why this priority**: Count corrections and write-offs are an everyday inventory need and must tie to the ledger (inventory is a real Asset account).

**Independent Test**: Can be fully tested by a `+2` then a `−3` adjustment on the US4 state and verifying the ledger inventory balance equals the stock-balance value.

**Acceptance Scenarios**:

1. **Given** a draft adjustment with a positive line quantity of 2 (avg cost 110), **When** it is posted, **Then** one balanced JE (Dr Inventory 220, Cr Adjustments 220), balance `qty 17 / value 1,870`, and one receipt-type movement are created.
2. **Given** a draft adjustment with a negative line quantity of −3, **When** it is posted, **Then** the JE is Dr Adjustments 330, Cr Inventory 330 (balance `qty 14 / value 1,540`).
3. **Given** a negative adjustment larger than on-hand quantity, **When** posted, **Then** it is rejected with no JE or movement.
4. **Given** a posted adjustment, **When** edit/delete is attempted, **Then** it is rejected (immutable).
5. **Given** an unconfigured adjustments account, **When** posting is attempted, **Then** it fails with a configuration error; drafts still work.

---

### User Story 6 - Inventory UI (Priority: P2)

The accountant sees an Inventory UI (Products / Stock / Adjustments / Settings) following the existing Cetrak design system, and existing purchase/sales invoice forms gain an optional product selector per line.

**Why this priority**: Delivers the feature to end users; depends on all backend stories.

**Independent Test**: Can be fully tested by creating a product, entering settings, posting a purchase invoice with the product, then a sales invoice, and reading balances/movements in the Stock page.

**Acceptance Scenarios**:

1. **Given** an inventory product, **When** a purchase invoice line selects it, **Then** posting increases the Stock page balance and shows the receipt movement.
2. **Given** the Stock page, **When** a sales invoice posts against the product, **Then** the balance decreases and the issue movement appears.
3. **Given** an unconfigured inventory account, **When** the Settings page is saved empty, **Then** the server rejects it (type-guarded), consistent with sales/purchases settings.

---

### Edge Cases

- Product from another tenant → `"Product not found."` (no disclosure).
- Product referenced on a purchase/sales invoice from another tenant → rejected at create/edit (tenant-scoped field).
- Duplicate `sku` within tenant → rejected.
- Deactivating a product referenced by posted or draft lines → rejected (PROTECT); unused products delete→deactivate.
- Purchase invoice with product lines but no inventory account / default warehouse / warehouse ownership mismatch → configuration error, no JE, no movement.
- Sales invoice with product lines but stock below quantity → `"Insufficient stock."`, no JE, no movement.
- **Two concurrent sales posts** that would consume the last units of the same product → serialized by `select_for_update` on the `StockBalance` row; one succeeds, the loser sees the updated balance and fails with "Insufficient stock."
- **Two concurrent purchase posts** for the same product → serialized by `select_for_update` on the balance row; both book correctly (receipts only ever increase stock).
- Weighted-average rounding — value is the authoritative aggregate; `moving_avg_cost` is a derived display snapshot (`value / quantity`), recomputed at each movement without accumulated drift.
- Purchase line with `tax_rate > 0` → tax remains a separate reclaimable **asset** line and is **not** capitalized into inventory cost.
- Services (lines without product) on the same invoice as stock lines → both legs coexist and the single JE still balances after proportional discount allocation.
- Cross-tenant balance/movement/adjustment/settings access → generic errors.
- Adjustment number duplication → rejected; posting an already-posted adjustment → rejected; adjustment JE reference `ADJ-INV-{n}` never duplicated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A user with the inventory manage permission MUST be able to create, edit, and deactivate **Products**; a product MUST have `tenant`, `sku` (unique per tenant), `name`, `unit`, `is_active`, and timestamps.
- **FR-002**: A product referenced by any purchase/sales line MUST NOT be hard-deleted; delete returns `400` (deactivate instead) — mirroring the customer/vendor pattern.
- **FR-003**: Each tenant MUST have a **default Warehouse**, auto-created lazily on first inventory use; warehouses are tenant-scoped and listed by the API.
- **FR-004**: **InventorySettings** MUST be a single row per tenant: `inventory_account` (Asset), `cogs_account` (Expense), `adjustments_account` (Expense), `default_warehouse` (Warehouse); type-guarded exactly like `SalesSettings`/`PurchaseSettings`.
- **FR-005**: **PurchaseInvoiceLine** MUST gain a nullable `product` FK (additive): a line with `product` → stock receipt on posting; a line without `product` → Feature 011 expense behaviour unchanged.
- **FR-006**: Posting a purchase invoice with any product line MUST, atomically and under row locks: create exactly one balanced JE splitting the Debit side into **Dr Inventory** (product-line net after proportional discount allocation) and **Dr Expense** (service-line net), **Dr Input VAT**, **Cr AP**; create one **receipt `StockMovement`** per product line; update `StockBalance` (qty, value, moving avg).
- **FR-007**: The stock receipt net cost must exclude VAT; discount MUST be allocated across lines proportionally to line subtotal so the summed Debit legs always equal `subtotal − discount`.
- **FR-008**: **SalesInvoiceLine** MUST gain a nullable `product` FK (additive): a line with `product` → stock issue on posting; a line without `product` → Feature 009 behaviour unchanged.
- **FR-009**: Posting a sales invoice with any product line MUST, atomically and under row locks: create exactly one balanced JE that adds **Dr COGS / Cr Inventory** (both = qty × weighted-average unit cost per product line) to the existing **Dr AR / Cr Revenue / Cr VAT** entry; create one **issue `StockMovement`**; update `StockBalance`.
- **FR-010**: Stock MUST never go negative — a sales-issue or negative adjustment exceeding on-hand quantity MUST fail with `"Insufficient stock."` (or equivalent) and create no JE/movement.
- **FR-011**: Valuation MUST be **moving weighted average** per `(product, warehouse)`, with money as `Decimal(19,4)` and no `float` anywhere; receipts update the average, issues consume it.
- **FR-012**: **StockMovement** MUST be an immutable append-only ledger (type, signed quantity, unit_cost, value, product, warehouse, source document) — never edited or deleted once created; `StockBalance.quantity == Σ movement.quantity` and `StockBalance.value == Σ movement.value`.
- **FR-013**: **StockAdjustment** MUST follow `Draft → Posted`: user-supplied `number` unique per tenant, date, reason, signed per-line quantities; posting creates movement(s) and one balanced JE `ADJ-INV-{number}` (Dr/Cr Inventory ↔ Cr/Dr Adjustments at current weighted-average cost) under row locks; posted adjustments are immutable.
- **FR-014**: All queries MUST be tenant-scoped (`.for_tenant(request.tenant_id)`); cross-tenant products/warehouses/balances/movements/adjustments/accounts MUST produce generic errors with no disclosure.
- **FR-015**: No hard-coded account, tenant, or warehouse IDs; no changes to the `apps/accounting` schema, `SalesSettings`, or `PurchaseSettings` semantics.
- **FR-016**: Permissions MUST reuse the existing role system with inventory analogues: `CanViewInventory`, `CanManageInventory` (products CRUD + adjustments create/post), `CanConfigureInventory` (settings); no new roles.
- **FR-017**: APIs MUST follow existing versioned routing and DRF conventions: products, warehouses, stock balances (read), movements (read), adjustments (+ posting action), settings under `api/v1/inventory/`.
- **FR-018**: Multi-warehouse **transfers**, batch/lot/serial tracking, expiry, sales returns/credit notes, manufacturing/BOM, forecasting, FIFO/LIFO/standard costing, and automatic number sequences are **out of scope**; the documented correction path for a mistaken movement is a reversing `StockAdjustment`/manual reversing JE.

### Key Entities

- **Product**: tenant, `sku` (unique/tenant), `name`, `unit`, `is_active`, timestamps.
- **Warehouse**: tenant, `name`, `is_active`; a lazily-created default row per tenant.
- **InventorySettings**: tenant (unique), `inventory_account` (Asset), `cogs_account` (Expense), `adjustments_account` (Expense), `default_warehouse`.
- **StockBalance**: `product` + `warehouse` (unique per tenant product+warehouse), `quantity`, `value` (authoritative), `moving_avg_cost` (derived snapshot).
- **StockMovement**: product/warehouse, `movement_type` (Receipt/Issue/Adjustment), signed `quantity`, `unit_cost`, `value`, source FK (purchase invoice / sales invoice / adjustment), immutable.
- **StockAdjustment** (+ line): `number` (unique/tenant), `status`, `adjustment_date`, `reason`, signed per-line quantities; posting → movements + `ADJ-INV-{n}` JE.
- **Additive line FKs**: `PurchaseInvoiceLine.product` (nullable), `SalesInvoiceLine.product` (nullable).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Product CRUD round-trip works; duplicate sku rejected; used product rejects delete (`400`); cross-tenant access is `404` with a generic error.
- **SC-002**: The valuation sequence (10 @ 100, 10 @ 120, sell 5 @ 150) yields `avg = 110`, `COGS = 550`, balance `qty 15 / value 1,650`; every JE in the sequence is balanced.
- **SC-003**: Purchase posting with product lines produces one balanced JE with a Dr Inventory leg, one receipt movement per product line, correct balance updates, and no drift; service-line purchase posts behave exactly as Feature 011.
- **SC-004**: Sales posting with product lines produces one balanced JE with a Dr COGS / Cr Inventory leg; insufficient stock is rejected with no JE/movement; service-line sales posts behave exactly as Feature 009.
- **SC-005**: Adjustment posting (+2, −3 on the SC-002 state) produces movements and balanced JEs; the ledger balance of the inventory account equals `StockBalance.value`.
- **SC-006**: Zero cross-tenant leakage across products, balances, movements, adjustments, settings, and account mappings — the Feature 010/011 tenant-isolation test pattern passes for inventory.
- **SC-007**: Full backend regression stays green at 223 tests and grows by the new inventory suite; frontend build passes; new files lint-clean (16 pre-existing issues only); existing purchase/sales invoice forms work unchanged without a product selected.

## Assumptions

- **Valuation**: moving weighted average (chosen over FIFO for MVP arithmetic simplicity; FIFO documented as future work).
- **Currency**: single-currency system (existing assumption) — no currency field.
- **Product select is optional on lines**: grab-bag/service lines keep posting to the expense account, preserving Features 009/011 behaviour for non-stock purchases and sales.
- **Numbering**: user-supplied adjustment numbers unique per tenant (mirrors invoices/payments; auto-sequencing deferred).
- **VAT**: taxable purchase lines capitalize only the net (tax-exclusive) cost; output/input VAT legs use the existing configured VAT accounts and are not part of inventory valuation.
- **Warehouses**: single default warehouse per tenant in MVP; the entity exists to make later multi-warehouse work a pure additive migration (per-warehouse balances already built in).
- **Corrections**: mistaken movements are corrected by a reversing `StockAdjustment` (and manual reversing JE where needed), not by editing the ledger.
- **Dependency**: Requires the accounting core, Features 009 (sales posting), 010 (payment/list architecture), and 011 (purchases posting + settings patterns). `apps/inventory` is a new app that must be added to `INSTALLED_APPS`.