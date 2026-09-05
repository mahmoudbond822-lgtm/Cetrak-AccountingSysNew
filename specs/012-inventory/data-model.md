# Data Model: Inventory Management (Feature 012)

## 1. New App: `apps/inventory`

All seven tables live in a new `apps/inventory` app (added to `INSTALLED_APPS` in `config/settings/base.py`). Migration `apps/inventory/migrations/0001_initial.py`. `apps/purchases` gains one additive migration (`0002`), `apps/sales` one additive migration (`0004`). No changes to `apps/accounting` schema, `SalesSettings`, or `PurchaseSettings`.

### 1.1 `inventory_product`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK core.Tenant | Tenant isolation; set from `request.tenant_id`. |
| `id`, `created_at`, `updated_at` (inherited) | UUID / DateTime | BaseModel. |
| `sku` | Char(50) | **Required**, stripped. Unique per tenant. |
| `name` | Char(255) | **Required**, stripped. |
| `unit` | Char(50) | **Required** (e.g. `pcs`, `kg`, `box`). |
| `is_active` | Boolean | default True; delete-with-use → deactivate. |

Constraints/indexes:

```python
constraints = [UniqueConstraint(fields=["tenant", "sku"], name="unique_product_sku_per_tenant")]
indexes = [Index(fields=["tenant"]), Index(fields=["is_active"])]
```

### 1.2 `inventory_warehouse`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Tenant isolation. |
| `name` | Char(255) | **Required**, stripped. |
| `is_active` | Boolean | default True. |

- A **default warehouse** per tenant is created lazily by `InventorySettingsService.get()` ("Default"), enclosed in `transaction.atomic()` with `get_or_create`.
- No dedicated delete API in MVP (tenants operate a single warehouse; the entity exists to future-proof transfer features).

```python
constraints = [UniqueConstraint(fields=["tenant", "name"], name="unique_warehouse_name_per_tenant")]
indexes = [Index(fields=["tenant"])]
```

### 1.3 `inventory_settings`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Unique per tenant. |
| `inventory_account` | FK → `accounting.Account` (PROTECT, `related_name="+"`), null/blank | **Asset**. Dr on purchase receipt; Cr on sales issue/adjustment. |
| `cogs_account` | FK → `accounting.Account` (PROTECT, `related_name="+"`), null/blank | **Expense**. Dr on sales issue (COGS). |
| `adjustments_account` | FK → `accounting.Account` (PROTECT, `related_name="+"`), null/blank | **Expense**. Dr on negative adjustment / Cr on positive adjustment. |
| `default_warehouse` | FK → `inventory.warehouse` (PROTECT, `related_name="+"`), null/blank | Created lazily. Required before any stock posting. |

```python
constraints = [UniqueConstraint(fields=["tenant"], name="unique_inventory_settings_per_tenant")]
```

### 1.4 `inventory_stockbalance`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Tenant isolation. |
| `product` | FK → `inventory_product` (PROTECT, `related_name="balances"`) | — |
| `warehouse` | FK → `inventory_warehouse` (PROTECT, `related_name="balances"`) | — |
| `quantity` | DecimalField(19,4) | On-hand qty; `≥ 0`. |
| `value` | DecimalField(19,4) | **Authoritative** inventory value (`Σ movement values`). |
| `moving_avg_cost` | DecimalField(19,4) | Display snapshot = `value / quantity` when qty > 0 else 0; recomputed at each movement (no accumulated drift). |

Constraints:

```python
constraints = [UniqueConstraint(fields=["tenant", "product", "warehouse"], name="unique_stockbalance_per_product_warehouse")]
indexes = [Index(fields=["tenant", "product", "warehouse"])]
```

The row is the **lock unit** for all concurrency (research D11). Invariant (asserted in tests): `quantity == Σ movements.quantity`, `value == Σ movements.value`.

### 1.5 `inventory_stockmovement`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Tenant isolation. |
| `product` | FK → `inventory_product` (PROTECT, `related_name="movements"`) | — |
| `warehouse` | FK → `inventory_warehouse` (PROTECT, `related_name="movements"`) | — |
| `movement_type` | Char(20) | `Receipt` / `Issue` / `Adjustment`. |
| `quantity` | DecimalField(19,4) | **Signed** (positive = increase, negative = decrease). |
| `unit_cost` | DecimalField(19,4) | Cost snapshot of this movement (`≥ 0`). |
| `value` | DecimalField(19,4) | `quantity × unit_cost` (signed). |
| `purchase_invoice` | FK → `purchases.PurchaseInvoice` (PROTECT, `related_name="stock_movements"`), null | Set for `Receipt`. Lazy string reference. |
| `sales_invoice` | FK → `sales.SalesInvoice` (PROTECT, `related_name="stock_movements"`), null | Set for `Issue`. Lazy string reference. |
| `adjustment` | FK → `inventory_stockadjustment` (PROTECT, `related_name="stock_movements"`), null | Set for `Adjustment`. |

```python
indexes = [Index(fields=["tenant", "product", "warehouse"]), Index(fields=["tenant", "movement_type"]), Index(fields=["purchase_invoice"]), Index(fields=["sales_invoice"]), Index(fields=["adjustment"])]
ordering = ["created_at"]
```

**Immutable**: no update/delete API; every stock change is a new row tied to a posted document.

### 1.6 `inventory_stockadjustment`

| Field | Type | Rules |
|---|---|---|
| `tenant` (inherited) | FK | Tenant isolation. |
| `number` | Char(50) | **Required**, unique per tenant. |
| `status` | Char(20), default `Draft` | `Draft` → `Posted`. |
| `adjustment_date` | DateField | Required. |
| `reason` | Char(255) | Required. |
| `posted_journal` | OneToOne → `accounting.JournalEntry` (PROTECT, `related_name="stock_adjustment"`), null/blank | Set at posting; blocks double posting. |
| `posted_at` | DateTimeField | null; set at posting. |

```python
constraints = [UniqueConstraint(fields=["tenant", "number"], name="unique_adjustment_number_per_tenant")]
indexes = [Index(fields=["tenant", "status"]), Index(fields=["tenant", "adjustment_date"])]
ordering = ["-created_at"]
```

### 1.7 `inventory_stockadjustmentline`

| Field | Type | Rules |
|---|---|---|
| `id`, `created_at`, `updated_at` (inherited) | BaseModel | — |
| `adjustment` | FK → `stockadjustment` (CASCADE, `related_name="lines"`) | — |
| `product` | FK → `inventory_product` (PROTECT) | Required. |
| `quantity` | DecimalField(19,4) | **Signed**; `≠ 0`. Positive = add stock, negative = remove. |

## 2. Modified tables (additive, both nullable)

### 2.1 `purchase_invoiceline` (adds column — `apps/purchases`, migration `0002`)

| Change | Detail |
|---|---|
| `product` (new) | FK → `inventory_product` (PROTECT, `related_name="+""`, **null=True**) — optional reference; `null` preserves Feature 011 behaviour (post to expense, no movement). |

### 2.2 `sales_invoiceline` (adds column — `apps/sales`, migration `0004`)

| Change | Detail |
|---|---|
| `product` (new) | FK → `inventory_product` (PROTECT, `related_name="+"`, **null=True**) — optional reference; `null` preserves Feature 009 behaviour (revenue only, no COGS, no movement). |

No data migrations; reverse operations are symmetric `RemoveField`s.

## 3. Relationships (ER summary)

```
Tenant 1───* Product *───1 …1 StockBalance 1(lock unit)─── product/warehouse
Tenant 1───* Warehouse *───1 …
Product *───1 StockMovement ───0..1 PurchaseInvoice | SalesInvoice | StockAdjustment
StockAdjustment 1───* StockAdjustmentLine *───1 Product
PurchaseInvoiceLine (nullable product)   [modified]
SalesInvoiceLine      (nullable product)   [modified]
InventorySettings 1───0..1 Account (inventory_account / cogs_account / adjustments_account)
InventorySettings 1───0..1 Warehouse (default_warehouse)
```

## 4. Valuation arithmetic (moving weighted average)

Authoritative storage: `balance.value`; derived snapshot: `moving_avg_cost = value / quantity` (with qty > 0).

Receipt (`in_qty > 0`, `in_unit_cost`):
```
new_value   = balance.value + in_qty × in_unit_cost
new_qty     = balance.quantity + in_qty
new_avg     = new_value / new_qty
```

Issue (`out_qty`, consumes current avg):
```
consumed    = out_qty × moving_avg_cost
new_value   = balance.value − consumed
new_qty     = balance.quantity − out_qty
```

Guard: `out_qty ≤ balance.quantity` (negative-stock invariant).

Adjustment (signed `q`): if `q > 0` treat as a receipt; if `q < 0` treat as an issue of `|q|` (with the negative-stock guard), `value = |q| × moving_avg_cost`.

## 5. Journal Entries produced

### 5.1 Purchase invoice posting (`PUR-INV-{number}`) — inventory-aware

Allocation: `line_net_i = line_subtotal_i − discount × (line_subtotal_i / subtotal)`.

| Line | Account (source) | Debit | Credit |
|---|---|---|---|
| 1 | `inventory_account` (settings) | Σ product-line `line_net` | — |
| 2 | `expense_account` (purchase settings) | Σ service-line `line_net` | — |
| 3 | `input_vat` (purchase settings, only if tax > 0) | `tax` | — |
| 4 | `accounts_payable` (purchase settings) | — | `total` |

Balanced by construction: `Σ line_net = subtotal − discount`, so `Dr = (subtotal − discount) + tax = total = Cr`. When no line references a product this degenerates to the exact Feature 011 JE.

### 5.2 Sales invoice posting (`SALES-INV-{number}`) — inventory-aware

`COGS = Σ_product_lines qty × moving_avg_cost` (after the row lock).

Existing legs (Feature 009) + additive self-balancing pair:

| Line | Account (source) | Debit | Credit |
|---|---|---|---|
| 1 | `accounts_receivable` (sales settings) | `total` | — |
| 2 | `sales_revenue` (sales settings) | — | `subtotal − discount` |
| 3 | `vat_payable` (sales settings, if tax > 0) | — | `tax` |
| 4 | `cogs_account` (inventory settings) | `COGS` | — |
| 5 | `inventory_account` (inventory settings) | — | `COGS` |

Balanced because lines 4–5 net to zero on an already-balanced entry.

### 5.3 Adjustment posting (`ADJ-INV-{number}`)

Per line (signed `q`, `v = |q| × moving_avg_cost`):

| Direction | Line | Account | Debit | Credit |
|---|---|---|---|---|
| `q > 0` | 1 | `inventory_account` | `v` | — |
| `q > 0` | 2 | `adjustments_account` | — | `v` |
| `q < 0` | 1 | `adjustments_account` | `v` | — |
| `q < 0` | 2 | `inventory_account` | — | `v` |

Multiple lines aggregate into the single JE; balanced line-by-line. Negative-stock guard applied to every negative line.

## 6. Why these choices

- **`StockBalance` maintained + `StockMovement` immutable ledger**: fast reads/locks plus full auditability, and the `balance == Σ movements` invariant gives an automatic money-drift check (asserted in tests).
- **Moving weighted average over FIFO**: the brief permits either; weighted average is a single per-product number (framed in the existing Decimal discipline), needs no cost-layers and no lot bookkeeping, and is what most SME ERPs start with. FIFO the natural future upgrade (documented).
- **Warehouse entity + default row instead of a tenant-wide balance**: makes multi-warehouse a pure additive change and gives every movement a warehouse FK now, at near-zero MVP cost.
- **Additive nullable `product` FKs**: invoice lines without a product stay service lines — the exact Feature 009/011 posting paths are preserved, which is the strongest possible regression guarantee.
- **Optional stock on purchase but VAT always excluded from cost**: reclaimable input VAT is an asset leg, not part of capitalised inventory cost (research Q14).
- **`PROTECT` on every stock FK**: products/warehouses/documents that fed the ledger (movements, balances, posted adjustments, settings accounts) can never be silently destroyed; product delete-with-use → deactivate (customers/vendors pattern).

## 7. Migrations

1. `apps/inventory/migrations/0001_initial.py` — creates `inventory_product`, `inventory_warehouse`, `inventory_settings`, `inventory_stockbalance`, `inventory_stockmovement`, `inventory_stockadjustment`, `inventory_stockadjustmentline` (+ constraints/indexes).
2. `apps/purchases/migrations/0002_add_product_to_purchase_invoiceline.py` — adds nullable `product` FK (depends on inventory `0001`).
3. `apps/sales/migrations/0004_add_product_to_sales_invoiceline.py` — adds nullable `product` FK (depends on inventory `0001`).

No data migrations; reverse operations are symmetric drops/removes.