<!-- SPECKIT START -->
Implementation plan: specs/012-inventory/plan.md

Current phase: PLANNING — Feature 012 (Inventory Management) spec artifacts drafted (spec, plan, research, data-model, tasks, quickstart, contracts, checklist); awaiting review. NOT implemented. Do not push or deploy.

## What This Feature Does

Inventory Management — perpetual stock-keeping integrated directly with the Accounting system: **Purchase → Stock Receipt → Inventory → Sales → Stock Issue → COGS → Accounting**. A new `apps/inventory` app owns the tenant-scoped product catalog (`Product`), a single default `Warehouse` (lazily created per tenant), a maintained `StockBalance` (quantity, value, moving-average cost) backed by an immutable append-only `StockMovement` ledger, and `StockAdjustment` drafts that post balanced `ADJ-INV-{number}` journal entries. Product lines on purchase invoices post a stock receipt (Dr Inventory, Dr Input VAT, Cr AP — net after proportional discount, VAT excluded from cost); product lines on sales invoices post a stock issue plus **Dr COGS / Cr Inventory** at the moving weighted-average cost inside the existing balanced `SALES-INV-{number}` entry. Non-product (service) lines keep Features 009/011 behavior byte-for-byte via additive nullable `product` FKs. Negative stock is hard-rejected; posting is atomic, row-locked (`select_for_update` on `StockBalance` rows in a stable order), idempotent (unique `(tenant, reference)`), and tenant-isolated.

## Generated Artifacts

- `specs/012-inventory/spec.md` — Feature specification (draft)
- `specs/012-inventory/plan.md` — Implementation plan (draft)
- `specs/012-inventory/research.md` — Technical research, incl. the 20-question decision table (draft)
- `specs/012-inventory/data-model.md` — Data model (draft)
- `specs/012-inventory/contracts/inventory-api.md` — Inventory API contracts (draft)
- `specs/012-inventory/quickstart.md` — Validation scenarios (draft, to verify at implementation)
- `specs/012-inventory/tasks.md` — Implementation tasks (all complete)
- `specs/012-inventory/checklists/requirements.md` — Spec quality checklist (draft, to verify at close-out)

## Key Decisions (locked in the plan)

- New `apps/inventory` app (must be added to INSTALLED_APPS) with `Product`, `Warehouse`, `InventorySettings`, `StockBalance`, `StockMovement`, `StockAdjustment` (+ line).
- Moving weighted average per `(product, warehouse)`; `value` is the authoritative aggregate, `moving_avg_cost = value / quantity` is a display snapshot; invariant `balance == Σ movements` asserted in tests.
- One default `Warehouse` created lazily per tenant; multi-warehouse transfers deferred (schema already keyed on warehouse).
- Additive nullable `product` FKs on `PurchaseInvoiceLine` (purchases migration `0002`) and `SalesInvoiceLine` (sales migration `0004`); no changes to `apps/accounting`, `SalesSettings`, or `PurchaseSettings`.
- Purchase posting leg split: Dr Inventory (product-line nets after proportional discount) + Dr Expense (service-line nets) + Dr Input VAT + Cr AP — sums to `subtotal − discount + tax` = total.
- Sales posting adds the self-balancing Dr COGS / Cr Inventory pair (qty × weighted-average cost) to the existing AR/Revenue/VAT entry.
- Negative stock hard-rejected at posting (row-locked, atomic, zero artifacts on failure). Adjustments `Draft → Posted` with balanced `ADJ-INV-{number}` JE at current avg cost.
- Permissions: `CanViewInventory` / `CanManageInventory` (products + adjustments incl. posting) / `CanConfigureInventory`; no separate `CanPost*` (stock effects ride the source document's permission — documented deviation).
- Deferred (per brief): transfers, batch/lot/serial, expiry, returns/credit notes, manufacturing/BOM, forecasting, FIFO/standard costing, auto-numbering.

## Next Steps (after review)

- Review the plan, then either adjust scope or proceed to implementation (Phases 1–7 in plan.md). Do not push or deploy; commit artifacts only via the auto-commit hook.

## Quick Reference

- Backend tests: `cd backend && py -m pytest apps/ -q` (current baseline 223 passing; must stay green, then grows with the inventory suite; DJANGO_SETTINGS_MODULE=config.settings.test)
- Planned inventory URLs: `api/v1/inventory/products/`, `api/v1/inventory/warehouses/`, `api/v1/inventory/stock-balances/`, `api/v1/inventory/stock-movements/`, `api/v1/inventory/adjustments/` (+ `{id}/post_adjustment/`), `api/v1/inventory/settings/current/`
- Existing sales/purchases URLs unchanged; invoice line payloads gain additive optional `product_id`
- Frontend: `npm run build` and `npm run lint` in `frontend/` (16 pre-existing problems in earlier feature files; new files must stay clean)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->