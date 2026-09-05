# Spec Quality Checklist: Inventory Management (Feature 012)

Status per item: `[x]` verified (expected at implementation close-out), `[ ]` not yet verified (planning).

## A. Feature Specification (`spec.md`)

- [ ] A1 — Feature name, branch, and source user-description recorded (`012-inventory`, "Inventory Management … Purchase → Stock Receipt → Inventory → Sales → Stock Issue → COGS → Accounting" quoted).
- [ ] A2 — Mandatory section present with ≥ 5 User Stories, each with accepted scenarios and explicit priority/Why.
- [ ] A3 — A testable acceptance deliverable (the 10 @ 100 / 10 @ 120 → sell 5 weighted-average sequence and COGS 550) is explicit.
- [ ] A4 — Acceptance Scenarios are complete, consistent, and use positive + negative cases (edge cases section present).
- [ ] A5 — Document map (spec/plan/research/data-model/tasks/quickstart/contracts/checklists) is referenced for each artifact written.
- [ ] A6 — FR-00x tags unique and traceable into tasks.md and research decisions.
- [ ] A7 — Every FR, ASSUMPTION, and DECISION in the spec is referenced elsewhere (research/data-model/quickstart).
- [ ] A8 — No Unsatisfied Custom Requirements: purchases→receipt, inventory catalog & balances, sales→issue, COGS→accounting, VAT, adjustments, tenant isolation, "no advanced features unless proven" all covered.
- [ ] A9 — Lifecycle/state coverage: Product active/inactive; StockMovement immutable/append-only; Adjustment Draft → Posted with immutability after posting.
- [ ] A10 — Success Criteria measurable and each maps to ≥ 1 algorithm/AC covering it (SC-001…SC-007).

## B. Implementation Plan (`plan.md`)

- [ ] B1 — Phases ordered correctly (app+models → migrations → services → serializers/views → tests → frontend → docs).
- [ ] B2 — Only the strict minimum files are changed directly: new `apps/inventory`, `config/settings/base.py` (INSTALLED_APPS), additive `purchases 0002` + `sales 0004` migrations, `config/urls.py` include, frontend mirror files.
- [ ] B3 — Design decisions table coherent with research.md D1–D14 (no conflicts).
- [ ] B4 — Sanity checks: weighted-average walkthrough and mixed-stock/discount example both balance; `Σ line_net = subtotal − discount` proven.
- [ ] B5 — No changes to `apps/accounting` schema, `SalesSettings`, `PurchaseSettings`, or payment behavior.

## C. Technical Research (`research.md`)

- [ ] C1 — Features 009/010/011/accounting conventions surveyed correctly (row-lock + unique reference + atomic pattern; sales/purchases posting JEs).
- [ ] C2 — All 20 research questions answered in a decision table with an implementation consequence.
- [ ] C3 — Valuation method chosen and justified (moving weighted average over FIFO/LIFO/standard); value-as-authoritative + avg-as-snapshot documented.
- [ ] C4 — Sales/purchases integration impact analyzed: additive nullable product FKs, leg-split JE, proportional discount allocation, COGS self-balancing pair.
- [ ] C5 — Risks identified for the highest-risk paths: regression of 009/011 posting, concurrent last-unit issues (ordered `select_for_update`), avg-cost drift (Σ-value invariant), over-engineering non-goals.

## D. Data Model (`data-model.md`)

- [ ] D1 — Base tables hold: tenant FK, UUID pk, timestamps (via TenantScopedModel/BaseModel).
- [ ] D2 — Money and quantities as `Decimal(19,4)` throughout; no float; `compute_line_totals` reused.
- [ ] D3 — Constraints: per-tenant unique product sku / warehouse name / adjustment number; single settings row per tenant; unique `(product, warehouse)` balance.
- [ ] D4 — `StockMovement` immutable + source FKs (purchase_invoice / sales_invoice / adjustment); PROTECT on-delete for all stock FKs; lines CASCADE.
- [ ] D5 — Posting JEs precisely itemized with source accounts and directions (PUR-INV Dr Inventory/Dr Expense/Dr VAT/Cr AP; SALES-INV + Dr COGS/Cr Inventory; ADJ-INV Dr/Cr Inventory ↔ Cr/Dr Adjustments).
- [ ] D6 — Valuation arithmetic documented (receipt avg update, issue consumption, negative-stock guard) with the walking example reconciled to the ledger.

## E. API Contracts (`contracts/inventory-api.md`)

- [ ] E1 — Endpoints, methods, status codes (200/201/204/400/401/403/404) and error bodies for products.
- [ ] E2 — Read-only warehouses, stock balances, and stock movements endpoints with filters documented.
- [ ] E3 — Adjustment endpoints (draft CRUD + `post_adjustment`) with `ADJ-INV-{n}` JE and errors.
- [ ] E4 — Settings `GET/PUT current/` include account-type validation, `*_name` fields for the UI, and lazy default-warehouse creation.
- [ ] E5 — Additive `product_id` on existing purchase/sales invoice line payloads documented (no route/semantics change; null = Feature 009/011 behavior).
- [ ] E6 — Tenant isolation enforced via `.for_tenant()` + generic (non-disclosing) error details.

## F. Quickstart (`quickstart.md`)

- [ ] F1 — Realistic, runnable end-to-end including the weighted-average walkthrough (10 @ 100, 10 @ 120, sell 5 → avg 110, COGS 550) and post-posting JE verification.
- [ ] F2 — Economics anti-cheese: duplicate sku, insufficient stock, over-negative adjustment, posted edits, service-line regression (009/011 unchanged), mixed stock+service+discount balancing, settings type guards covered.
- [ ] F3 — Ledger tie-out step (inventory account balance == balance.value == Σ movements) and regression command (`py -m pytest apps/ -q` → 223 baseline green) documented.

## G. Cross-Check Logic

- [ ] G1 — Cross-reference: SC-001↔Product AC; SC-002↔Valuation AC; SC-003↔Purchase-post AC; SC-004↔Sales-post AC; SC-005↔Adjustment AC; SC-006↔tenant isolation; SC-007↔regression+frontend.
- [ ] G2 — Every FR-00x maps to an AC, and every AC maps back to ≥ 1 FR-00x (bijective coverage).
- [ ] G3 — No AI-pattern drift: no float money, no hard-coded account/tenant/warehouse ids, no new roles beyond the three inventory permissions, no schema change to accounting/sales/purchases beyond the two additive nullable FKs, no unsupported frontend patterns.

## H. Spec Self-Check (deliverables vs review gate)

- [ ] H1 — All artifacts live under `specs/012-inventory/` mirroring the 011 layout (spec/plan/research/data-model/tasks/quickstart/contracts/ + checklists/requirements.md).
- [ ] H2 — Artifacts are the ONLY changes on branch `012-inventory` (clean tree, feature.json/AGENTS.md already updated to PLANNING).
- [ ] H3 — Committed via the repo auto-commit hook; `.specify/feature.json` points to `012-inventory`; AGENTS.md phase = PLANNING.