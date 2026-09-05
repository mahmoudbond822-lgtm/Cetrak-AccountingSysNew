# API Contracts: Inventory Management (Feature 012)

All endpoints require JWT auth + a resolved tenant (`X-Tenant-ID`); every query uses `objects.for_tenant(request.tenant_id)`. Unauthorized → `401`; wrong role → `403`; cross-tenant ids → generic `404`/`400` messages with no disclosure. Money and quantities are strings in `Decimal(19,4)`; never floats.

Permissions: **View** = `CanViewInventory` (Admin/Accountant/Manager); **Manage** = `CanManageInventory` (Admin/Accountant); **Configure** = `CanConfigureInventory` (Admin).

## Base URL

`/api/v1/inventory/`

---

## Products

### `GET /api/v1/inventory/products/` — list (View)
Query: `?is_active=`, `?search=` (sku/name icontains, optional). → `200`

```json
[{"id": "<uuid>", "sku": "SKU-001", "name": "Widget 20mm", "unit": "pcs",
  "is_active": true, "created_at": "...", "updated_at": "..."}]
```

### `POST /api/v1/inventory/products/` — create (Manage)
Body `{"sku": "SKU-001", "name": "Widget 20mm", "unit": "pcs"}` → `201`. `sku` stripped, unique per tenant.
Errors: duplicate `sku` → `400` `{"sku": ["SKU already exists."]}`; blank `sku`/`name`/`unit` → `400`.

### `GET /api/v1/inventory/products/{id}/` — retrieve (View)
Cross-tenant → `404` `{"detail": "Product not found."}`.

### `PUT` / `PATCH /api/v1/inventory/products/{id}/` — update (Manage)
`is_active = false` allowed directly (deactivate). Editing `sku` to a duplicate → `400`.

### `DELETE /api/v1/inventory/products/{id}/` — delete (Manage)
- Product referenced by any purchase/sales/adjustment line → `400` `{"detail": "Product is used by invoice lines and cannot be deleted. Deactivate instead."}` (no hard delete; PROTECT).
- Unused product → `204`, `is_active = false` (soft-delete to the deactivate pattern).

---

## Warehouses

### `GET /api/v1/inventory/warehouses/` — list (View)
Read-only. Returns the lazily-created default row:

```json
[{"id": "<uuid>", "name": "Default", "is_active": true}]
```

No create/update/delete endpoints in MVP (tenant operates a single warehouse; the entity exists to future-proof transfers).

---

## Stock Balances (View)

### `GET /api/v1/inventory/stock-balances/`
Query filters: `?product=`, `?warehouse=`. Ordering: product name. → `200`

```json
[{"id": "<uuid>", "product_id": "<uuid>", "product_name": "Widget 20mm", "product_sku": "SKU-001",
  "warehouse_id": "<uuid>", "warehouse_name": "Default",
  "quantity": "15.0000", "value": "1650.0000", "moving_avg_cost": "110.0000"}]
```

### `GET /api/v1/inventory/stock-balances/{id}/`
Cross-tenant balance → `404` `{"detail": "Stock balance not found."}`.

---

## Stock Movements (View, read-only)

### `GET /api/v1/inventory/stock-movements/`
Query filters: `?product=`, `?warehouse=`, `?movement_type=Receipt|Issue|Adjustment`. Newest-first.

```json
[{"id": "<uuid>", "product_id": "<uuid>", "product_name": "Widget 20mm", "product_sku": "SKU-001",
  "warehouse_id": "<uuid>", "warehouse_name": "Default",
  "movement_type": "Receipt", "quantity": "10.0000", "unit_cost": "100.0000", "value": "1000.0000",
  "purchase_invoice_id": "<uuid>", "sales_invoice_id": null, "adjustment_id": null,
  "created_at": "..."}]
```

No POST/PUT/DELETE — the movement ledger is **append-only**.

---

## Stock Adjustments

### `POST /api/v1/inventory/adjustments/` — create draft (Manage)
Body:

```json
{"number": "ADJ-1", "adjustment_date": "2026-09-05", "reason": "Count gain",
 "lines": [{"product_id": "<uuid>", "quantity": "2"}], "notes": null}
```

→ `201`, `status: "Draft"`, computed fields (`value` per line and totals read back as null until posting). `quantity` is **signed and ≠ 0** (`400` otherwise); `number` unique per tenant.

### `GET /api/v1/inventory/adjustments/` — list (View)
Query: `?status=Draft|Posted`. Each item exposes `posted_journal_id` when posted.

### `GET /api/v1/inventory/adjustments/{id}/` — retrieve (View)
Cross-tenant → `404` `{"detail": "Adjustment not found."}`.

### `PUT /api/v1/inventory/adjustments/{id}/` — update draft (Manage)
Rules mirror purchase/sales drafts: lines can change while `Draft`; `Posted` → `400` "Only draft adjustments can be edited."; duplicate `number` → `400`.

### `DELETE /api/v1/inventory/adjustments/{id}/` — delete draft (Manage)
`Draft` → `204`; `Posted` → `400`.

### `POST /api/v1/inventory/adjustments/{id}/post_adjustment/` — post (Manage)
Effects (atomic, row-locked on `StockBalance`): one balanced JE `ADJ-INV-{number}` at current weighted-average cost (Dr/Cr Inventory ↔ Cr/Dr adjustments_account), movement(s), updated balances, adjustment `Posted`.
Errors:
- Non-draft → `400` "Only draft adjustments can be posted."
- Settings missing `adjustments_account`/`inventory_account` or warehouse → `400` "Inventory accounting settings are not configured."
- Negative line larger than on hand → `400` "Insufficient stock." (nothing created).
- Duplicate post → `400` (status guard); duplicate JE reference impossible (`ADJ-INV-{number}` unique).
- Cross-tenant account/warehouse → `400` generic settings error.

---

## Inventory Settings

### `GET /api/v1/inventory/settings/current/` — get (View)
Returns the single row; **creates** the row + the default warehouse lazily on first call:

```json
{"id": "<uuid>", "inventory_account": null, "inventory_account_name": null,
 "cogs_account": null, "cogs_account_name": null,
 "adjustments_account": null, "adjustments_account_name": null,
 "default_warehouse_id": "<uuid>", "default_warehouse_name": "Default"}
```

### `PUT /api/v1/inventory/settings/current/` — update (Configure)
Body (any subset):

```json
{"inventory_account": "<uuid>", "cogs_account": "<uuid>",
 "adjustments_account": "<uuid>", "default_warehouse_id": "<uuid>"}
```

→ `200`. Type guards (serializer + service): `inventory_account` **Asset**, `cogs_account` **Expense**, `adjustments_account` **Expense**. Wrong type → `400`; account from another tenant → `400` "… account does not exist."; warehouse from another tenant → `400` "Warehouse not found.". `*_name` fields returned for the UI (frontend `AccountSelect` lists all accounts; server remains authoritative).

---

## Modified existing endpoints (additive — no route/semantics change)

### Purchases — `POST/PUT /api/v1/purchases/invoices/` line payload
Adds optional `product_id` on each line object:

```json
{"lines": [{"product_id": "<uuid>", "description": "...", "quantity": "10",
            "unit_price": "100", "tax_rate": "5"}]}
```

- Cross-tenant product → `400` "Product not found." at create/edit.
- On posting, product lines capitalize to Inventory and create receipt movements; `null` lines post to Expense exactly as Feature 011.

### Sales — `POST/PUT /api/v1/sales/invoices/` line payload
Adds optional `product_id` on each line object (same shape). On posting, product lines book Dr COGS/Cr Inventory and create issue movements; `null` lines post revenue-only exactly as Feature 009.

---

## Error status code map

| Code | Meaning |
|---|---|
| `200` | OK (retrieve/list/update/settings) |
| `201` | Created (products, adjustments, invoice drafts) |
| `204` | Deleted / deactivated |
| `400` | Validation/business rule (duplicate sku, wrong account type, insufficient stock, over-negative adjustment, posted edit/delete, settings unconfigured, cross-tenant reference) |
| `401` | Not authenticated |
| `403` | Authenticated but lacking View/Manage/Configure permission |
| `404` | Not found (cross-tenant or missing; generic detail) |