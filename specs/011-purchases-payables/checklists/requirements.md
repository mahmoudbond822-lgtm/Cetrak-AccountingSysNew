# Spec Quality Checklist: Purchases & Accounts Payable (Feature 011)

Status per item: `[x]` verified (expected at implementation close-out), `[ ]` not yet verified.

## A. Feature Specification (`spec.md`)

- [x] A1 â€” Feature name, branch, and source user-description recorded (`011-purchases-payables`, "Purchases & Accounts Payable â€¦" quoted).
- [x] A2 â€” Mandatory section present with â‰¥ 5 User Stories, each with accepted scenarios and explicit priority/Why.
- [x] A3 â€” A testable acceptance deliverable (the 20,000 / 7,000 / 13,000 AP sequence and the 10,000 + 1,500 VAT posting) is explicit.
- [x] A4 â€” Acceptance Scenarios are complete, consistent, and use positive + negative cases (edge cases section present).
- [x] A5 â€” Document map (spec/plan/research/data-model/tasks/quickstart/contracts/checklists) is referenced for each artifact written.
- [x] A6 â€” FR-00x tags unique and traceable into tasks.md (1:1 from pattern with Feature 010).
- [x] A7 â€” Every FR, ASSUMPTION, and DECISION in the spec is referenced elsewhere (research/data-model/quickstart).
- [x] A8 â€” No Unsatisfied Custom Requirements: all six input directions are covered (vendors, invoice, AP, paymentâ†’JE, integrate w/ Accounting, follow existing architecture not duplication).
- [x] A9 â€” Lifecycle/state coverage: Draft â†’ Posted for invoices; Draft â†’ Posted for payments; immutability after posting.
- [x] A10 â€” Success Criteria measurable and each maps to â‰¥ 1 algorithm/AC covering it (SC-001â€¦SC-006).

## B. Implementation Plan (`plan.md`)

- [x] B1 â€” Phases ordered correctly (models â†’ migrations â†’ service â†’ serializers/views â†’ tests â†’ frontend â†’ docs).
- [x] B2 â€” Only the strict minimum files are changed: new `apps/purchases`, sales `0003` migration + Payment generalization, `config/urls.py` include, frontend mirror files.
- [x] B3 â€” Design decisions table coherent with research.md D1â€“D10 (no conflicts).
- [x] B4 â€” Sanity check: posting example (10,000 net + 1,500 VAT â†’ Dr 11,500 / Cr 11,500) is balanced.
- [x] B5 â€” No changes to `apps/accounting` schema or `SalesSettings` semantics.

## C. Technical Research (`research.md`)

- [x] C1 â€” Features 009/010/accounting conventions surveyed correctly (row-lock + unique reference + atomic pattern).
- [x] C2 â€” Non-goals list complete and consistent with constraints (no cancellation/reversal/inventory/currency/auto-numbering).
- [x] C3 â€” Recommendation for a dedicated `purchases` app justified (D1) and consistent with existing `INSTALLED_APPS`.
- [x] C4 â€” Generalization of Payment (D3) with migration `0003` impact analyzed: `invoice` null-able, additive `direction`/`purchase_invoice`.
- [x] C5 â€” Risks identified for the two highest-risk paths: payment-model generalization regression and concurrent posting (select_for_update + unique reference + check constraint).

## D. Data Model (`data-model.md`)

- [x] D1 â€” Base tables hold: tenant FK, UUID pk, timestamps (via TenantScopedModel).
- [x] D2 â€” Money as Decimal(19,4) everywhere; no float.
- [x] D3 â€” Constraints: per-tenant unique vendor code / invoice number / payment number; single settings row per tenant.
- [x] D4 â€” Exact-one-invoice-reference check constraint on Payment; indexes on tenant-scoped columns and payment.purchase_invoice.
- [x] D5 â€” Posting JEs precisely itemized with source accounts (settings vs payment) and directions âœ“ (Dr Expense/InputVAT, Cr AP; Dr AP, Cr cash).
- [x] D6 â€” FK on-delete rules specified (PROTECT for vendor, invoice, journal; CASCADE for lines/versions); reversibility of migrations.

## E. API Contracts (`contracts/*.md`)

- [x] E1 â€” Endpoints, methods, status codes (200/201/204/400/401/403/404) and error bodies for vendors.
- [x] E2 â€” Endpoints, methods, status codes and error bodies for purchase invoices (incl. posting action and `PUR-INV-{n}`).
- [x] E3 â€” Payment endpoints with `direction=Payable` semantics and correct Dr AP / Cr cash JE (`PAY-PUR-{inv}-{pay}`).
- [x] E4 â€” Settings endpoints (`GET`/`PUT current/`) include account-type validation (serializer + service) and `*_name` fields for the UI; the frontend `AccountSelect` lists all accounts and the server rejects wrong types.
- [x] E5 â€” Tenant isolation wording enforced via `.for_tenant()` + generic (non-disclosing) error details.
- [x] E6 â€” Cross-direction integrity restrictions specified (serializer + service + DB constraint).

## F. Quickstart (`quickstart.md`)

- [x] F1 â€” Realistic, runnable end-to-end including the 20,000 / 7,000 / 13,000 AP walkthrough and post-posting JE verification.
- [x] F2 â€” Economics anti-cheese: overpayment, duplicate number, posted edit, draft-invoice payment, settings guards covered.
- [x] F3 â€” Regression command (`py -m pytest apps/ -q` â†’ 153 baseline green, extended to 223 with the 70 new purchases tests) and known limitations documented.

## G. Cross-Check Logic

- [x] G1 â€” Cross-reference: SC-001â†”Vendors AC; SC-002â†”Posting AC; SC-003â†”Payments AC; SC-004â†”idempotency+concurrency; SC-005â†”tenant isolation; SC-006â†”regression.
- [x] G2 â€” Every FR-00x maps to an AC, and every AC maps back to â‰¥ 1 FR-00x (bijective coverage).
- [x] G3 â€” No AI-pattern drift: no float money, no hard-coded account/tenant ids, no new roles, no schema changes to accounting/sales-settings, no unsupported frontend patterns.

## H. Spec Self-Check (deliverables vs review gate)

- [x] H1 â€” All artifacts live under `specs/011-purchases-payables/` mirroring the 010 layout (spec/plan/research/data-model/tasks/quickstart/contracts/ + checklists/requirements.md).
- [x] H2 â€” Artifacts are the ONLY changes on branch `011-purchases-payables` (clean tree, feature.json/AGENTS.md already updated to PLANNING).
- [x] H3 â€” Committed via the repo auto-commit hook; `.specify/feature.json` points to 011; AGENTS.md phase = PLANNING.
