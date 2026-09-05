# Spec Quality Checklist: Purchases & Accounts Payable (Feature 011)

Status per item: `[x]` verified (expected at implementation close-out), `[ ]` not yet verified.

## A. Feature Specification (`spec.md`)

- [ ] A1 — Feature name, branch, and source user-description recorded (`011-purchases-payables`, "Purchases & Accounts Payable …" quoted).
- [ ] A2 — Mandatory section present with ≥ 5 User Stories, each with accepted scenarios and explicit priority/Why.
- [ ] A3 — A testable acceptance deliverable (the 20,000 / 7,000 / 13,000 AP sequence and the 10,000 + 1,500 VAT posting) is explicit.
- [ ] A4 — Acceptance Scenarios are complete, consistent, and use positive + negative cases (edge cases section present).
- [ ] A5 — Document map (spec/plan/research/data-model/tasks/quickstart/contracts/checklists) is referenced for each artifact written.
- [ ] A6 — FR-00x tags unique and traceable into tasks.md (1:1 from pattern with Feature 010).
- [ ] A7 — Every FR, ASSUMPTION, and DECISION in the spec is referenced elsewhere (research/data-model/quickstart).
- [ ] A8 — No Unsatisfied Custom Requirements: all six input directions are covered (vendors, invoice, AP, payment→JE, integrate w/ Accounting, follow existing architecture not duplication).
- [ ] A9 — Lifecycle/state coverage: Draft → Posted for invoices; Draft → Posted for payments; immutability after posting.
- [ ] A10 — Success Criteria measurable and each maps to ≥ 1 algorithm/AC covering it (SC-001…SC-006).

## B. Implementation Plan (`plan.md`)

- [ ] B1 — Phases ordered correctly (models → migrations → service → serializers/views → tests → frontend → docs).
- [ ] B2 — Only the strict minimum files are changed: new `apps/purchases`, sales `0003` migration + Payment generalization, `config/urls.py` include, frontend mirror files.
- [ ] B3 — Design decisions table coherent with research.md D1–D10 (no conflicts).
- [ ] B4 — Sanity check: posting example (10,000 net + 1,500 VAT → Dr 11,500 / Cr 11,500) is balanced.
- [ ] B5 — No changes to `apps/accounting` schema or `SalesSettings` semantics.

## C. Technical Research (`research.md`)

- [ ] C1 — Features 009/010/accounting conventions surveyed correctly (row-lock + unique reference + atomic pattern).
- [ ] C2 — Non-goals list complete and consistent with constraints (no cancellation/reversal/inventory/currency/auto-numbering).
- [ ] C3 — Recommendation for a dedicated `purchases` app justified (D1) and consistent with existing `INSTALLED_APPS`.
- [ ] C4 — Generalization of Payment (D3) with migration `0003` impact analyzed: `invoice` null-able, additive `direction`/`purchase_invoice`.
- [ ] C5 — Risks identified for the two highest-risk paths: payment-model generalization regression and concurrent posting (select_for_update + unique reference + check constraint).

## D. Data Model (`data-model.md`)

- [ ] D1 — Base tables hold: tenant FK, UUID pk, timestamps (via TenantScopedModel).
- [ ] D2 — Money as Decimal(19,4) everywhere; no float.
- [ ] D3 — Constraints: per-tenant unique vendor code / invoice number / payment number; single settings row per tenant.
- [ ] D4 — Exact-one-invoice-reference check constraint on Payment; indexes on tenant-scoped columns and payment.purchase_invoice.
- [ ] D5 — Posting JEs precisely itemized with source accounts (settings vs payment) and directions ✓ (Dr Expense/InputVAT, Cr AP; Dr AP, Cr cash).
- [ ] D6 — FK on-delete rules specified (PROTECT for vendor, invoice, journal; CASCADE for lines/versions); reversibility of migrations.

## E. API Contracts (`contracts/*.md`)

- [ ] E1 — Endpoints, methods, status codes (200/201/204/400/401/403/404) and error bodies for vendors.
- [ ] E2 — Endpoints, methods, status codes and error bodies for purchase invoices (incl. posting action and `PUR-INV-{n}`).
- [ ] E3 — Payment endpoints with `direction=Payable` semantics and correct Dr AP / Cr cash JE (`PAY-PUR-{inv}-{pay}`).
- [ ] E4 — Settings endpoints include account-type validation and `OPTIONS` metadata pattern for the UI.
- [ ] E5 — Tenant isolation wording enforced via `.for_tenant()` + generic (non-disclosing) error details.
- [ ] E6 — Cross-direction integrity restrictions specified (serializer + service + DB constraint).

## F. Quickstart (`quickstart.md`)

- [ ] F1 — Realistic, runnable end-to-end including the 20,000 / 7,000 / 13,000 AP walkthrough and post-posting JE verification.
- [ ] F2 — Economics anti-cheese: overpayment, duplicate number, posted edit, draft-invoice payment, settings guards covered.
- [ ] F3 — Regression command (`py -m pytest apps/ -q` → 153 green baseline) and known limitations documented.

## G. Cross-Check Logic

- [ ] G1 — Cross-reference: SC-001↔Vendors AC; SC-002↔Posting AC; SC-003↔Payments AC; SC-004↔idempotency+concurrency; SC-005↔tenant isolation; SC-006↔regression.
- [ ] G2 — Every FR-00x maps to an AC, and every AC maps back to ≥ 1 FR-00x (bijective coverage).
- [ ] G3 — No AI-pattern drift: no float money, no hard-coded account/tenant ids, no new roles, no schema changes to accounting/sales-settings, no unsupported frontend patterns.

## H. Spec Self-Check (deliverables vs review gate)

- [ ] H1 — All artifacts live under `specs/011-purchases-payables/` mirroring the 010 layout (spec/plan/research/data-model/tasks/quickstart/contracts/ + checklists/requirements.md).
- [ ] H2 — Artifacts are the ONLY changes on branch `011-purchases-payables` (clean tree, feature.json/AGENTS.md already updated to PLANNING).
- [ ] H3 — Committed via the repo auto-commit hook; `.specify/feature.json` points to 011; AGENTS.md phase = PLANNING.