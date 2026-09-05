# Requirements Checklist: Payments & Receipts (Feature 010)

## Traceability Matrix

| Req | Description (summary) | Tasks | Tests (plan) | Status |
|---|---|---|---|---|
| FR-001 | Create draft payment vs posted invoice (perm) | T-006, T-013 | T-016, T-019 | [x] |
| FR-002 | Exactly one invoice, tenant-scoped | T-006, T-013, T-014 | T-020 | [x] |
| FR-003 | number/date/amount/method/cash_account | T-001, T-011 | T-016, T-021 | [x] |
| FR-004 | Payment number unique per tenant | T-001, T-006 | T-023 | [x] |
| FR-005 | Overpayment rejected (≤ outstanding) | T-006, T-007, T-009 | T-017, T-018 | [x] |
| FR-006 | Outstanding = total − Σ posted | T-004, T-005, T-012 | T-016, T-017 | [x] |
| FR-007 | Only posted invoices receive payments | T-006, T-009 | T-019 | [x] |
| FR-008 | Drafts editable/deletable; posted immutable | T-007, T-008, T-013 | T-019 | [x] |
| FR-009 | Posting → one balanced JE (Dr cash, Cr settings-AR), idempotent | T-009 | T-016, T-019 | [x] |
| FR-010 | Atomicity + row lock on balance check | T-009 | T-018 (race semantics) | [x] |
| FR-011 | Missing/inactive AR config → post fails, draft still allowed | T-009 | T-022 | [x] |
| FR-012 | JE reference `PAY-INV-{invoice}-{number}`, unique per tenant | T-001, T-009 | T-023 | [x] |
| FR-013 | cash_account tenant/active/Asset | T-011 | T-021 | [x] |
| FR-014 | Invoice exposes paid_amount + outstanding_balance | T-012 | T-016, T-017 | [x] |
| FR-015 | Payment payload includes invoice, customer, status, JE, outstanding | T-011 | T-016 | [x] |
| FR-016 | Tenant isolation everywhere, no info disclosure | T-006, T-009, T-013 | T-020 | [x] |
| FR-017 | Reuse sales permissions; no new permission models | T-013 | manual/API | [x] |
| FR-018 | Reversal out of scope; manual reversing JE documented | T-008 (delete draft), docs | T-019 | [x] |

## User Stories

| Story | Priority | Coverage | Status |
|---|---|---|---|
| US1 Post payment to posted invoice | P1 | T-006, T-009, T-013 + T-016/T-019 | [x] |
| US2 Partial/multiple + outstanding + overpayment | P1 | T-004, T-005, T-012 + T-017/T-018 | [x] |
| US3 Manage drafts + posting guards | P2 | T-007, T-008 + T-019 | [x] |
| US4 Payments UI (list/create/edit/post) | P3 | T-025…T-028 + T-029 build/lint | [x] |

## Success Criteria

| Criterion | Verification | Status |
|---|---|---|
| SC-001 | API round-trip (create→post) in one request pair | T-016 | [x] |
| SC-002 | Outstanding consistent across invoice/payment/form | T-017 + manual | [x] |
| SC-003 | Zero overpayment postings book | T-018 | [x] |
| SC-004 | Zero double postings book | T-019 | [x] |
| SC-005 | Every posting → one balanced JE | T-016 + respect Decimal | [x] |
| SC-006 | No cross-tenant leakage | T-020 | [x] |

## Notes

- Money is `Decimal(19,4)`; no `float` in money paths (T-010).
- No changes to `apps/accounting` schema; single new table in `apps/sales` (T-002 verified).
- Posted payments have no reversal in v1 (FR-018); documented correction path is a manual reversing Journal Entry.
- Frontend new files are lint-clean; the 16 pre-existing lint errors in earlier feature files remain out of scope.
- T-028 deviation: create/edit/post use the page modal (single `/sales/payments` list route), mirroring the existing customers/invoices pattern instead of separate `/new` and `/:id` routes.