# Requirements Checklist: Payments & Receipts (Feature 010)

## Traceability Matrix

| Req | Description (summary) | Tasks | Tests (plan) | Status |
|---|---|---|---|---|
| FR-001 | Create draft payment vs posted invoice (perm) | T-006, T-013 | T-016, T-019 | [ ] |
| FR-002 | Exactly one invoice, tenant-scoped | T-006, T-013, T-014 | T-020 | [ ] |
| FR-003 | number/date/amount/method/cash_account | T-001, T-011 | T-016, T-021 | [ ] |
| FR-004 | Payment number unique per tenant | T-001, T-006 | T-023 | [ ] |
| FR-005 | Overpayment rejected (≤ outstanding) | T-006, T-007, T-009 | T-017, T-018 | [ ] |
| FR-006 | Outstanding = total − Σ posted | T-004, T-005, T-012 | T-016, T-017 | [ ] |
| FR-007 | Only posted invoices receive payments | T-006, T-009 | T-019 | [ ] |
| FR-008 | Drafts editable/deletable; posted immutable | T-007, T-008, T-013 | T-019 | [ ] |
| FR-009 | Posting → one balanced JE (Dr cash, Cr settings-AR), idempotent | T-009 | T-016, T-019 | [ ] |
| FR-010 | Atomicity + row lock on balance check | T-009 | T-018 (race semantics) | [ ] |
| FR-011 | Missing/inactive AR config → post fails, draft still allowed | T-009 | T-022 | [ ] |
| FR-012 | JE reference `PAY-INV-{invoice}-{number}`, unique per tenant | T-001, T-009 | T-023 | [ ] |
| FR-013 | cash_account tenant/active/Asset | T-011 | T-021 | [ ] |
| FR-014 | Invoice exposes paid_amount + outstanding_balance | T-012 | T-016, T-017 | [ ] |
| FR-015 | Payment payload includes invoice, customer, status, JE, outstanding | T-011 | T-016 | [ ] |
| FR-016 | Tenant isolation everywhere, no info disclosure | T-006, T-009, T-013 | T-020 | [ ] |
| FR-017 | Reuse sales permissions; no new permission models | T-013 | manual/API | [ ] |
| FR-018 | Reversal out of scope; manual reversing JE documented | T-008 (delete draft), docs | T-019 | [ ] |

## User Stories

| Story | Priority | Coverage | Status |
|---|---|---|---|
| US1 Post payment to posted invoice | P1 | T-006, T-009, T-013 + T-016/T-019 | [ ] |
| US2 Partial/multiple + outstanding + overpayment | P1 | T-004, T-005, T-012 + T-017/T-018 | [ ] |
| US3 Manage drafts + posting guards | P2 | T-007, T-008 + T-019 | [ ] |
| US4 Payments UI (list/create/edit/post) | P3 | T-025…T-028 + T-029 build/lint | [ ] |

## Success Criteria

| Criterion | Verification | Status |
|---|---|---|
| SC-001 | API round-trip (create→post) in one request pair | T-016 | [ ] |
| SC-002 | Outstanding consistent across invoice/payment/form | T-017 + manual | [ ] |
| SC-003 | Zero overpayment postings book | T-018 | [ ] |
| SC-004 | Zero double postings book | T-019 | [ ] |
| SC-005 | Every posting → one balanced JE | T-016 + respect Decimal | [ ] |
| SC-006 | No cross-tenant leakage | T-020 | [ ] |

## Notes

- Money is `Decimal(19,4)`; no `float` in money paths (T-010).
- No changes to `apps/accounting` schema; single new table in `apps/sales` (T-002 must confirm).
- Posted payments have no reversal in v1 (FR-018); documented correction path is a manual reversing Journal Entry.
- Frontend new files must be lint-clean; the 16 pre-existing lint errors in earlier feature files remain out of scope.