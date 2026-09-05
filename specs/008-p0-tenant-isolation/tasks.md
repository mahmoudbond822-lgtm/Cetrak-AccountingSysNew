---
description: "Task list for Feature 008 — P0 Tenant Isolation"
---

# Tasks: P0 Tenant Isolation

**Input**: Design documents from `specs/008-p0-tenant-isolation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/accounting-api.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/apps/accounting/`, `backend/apps/core/`
- **Tests**: `backend/apps/accounting/tests/`
- No frontend changes — backend-only isolation feature

---

## Phase 1: Setup

**Purpose**: Verify existing test infrastructure and read the current codebase to understand the vulnerable paths

- [X] T001 Read and understand `backend/apps/accounting/serializers.py` — identify the two vulnerable locations (AccountSerializer.validate_parent_id line 34 using `Account.objects.get()` without tenant scope, and JournalEntryLineSerializer.account_id field line 59 using `Account.objects.all()` without tenant scope)

- [X] T002 Read and understand `backend/apps/accounting/tests/test_accounting_api.py` — identify the existing `MultiTenantIsolationTests` class around line 937, its setup pattern, and the existing test methods to understand how to add new cross-tenant regression tests

- [X] T003 Run existing accounting tests to confirm they pass before making changes:
      `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/accounting/tests/ -v`

---

## Phase 2: Foundational (Tenant-Aware Serializer Context)

**Purpose**: Ensure accounting serializers have reliable access to the request's active tenant context, which is a prerequisite for both US1 and US2

- [X] T004 Confirm that `AccountSerializer` and `JournalEntryLineSerializer` can access `self.context['request'].tenant_id` during validation. If not, update the viewset's `get_serializer` calls to pass the request context. File: `backend/apps/accounting/views.py`

---

## Phase 3: User Story 1 + User Story 2 — Block Cross-Tenant References & Preserve Same-Tenant Work (Priority: P1) 🎯 MVP

**Goal**: Close the P0 gap by scoping every account reference in accounting write operations to the active tenant. Same-tenant workflows must continue unaffected.

**Independent Test**: Create two tenants with separate accounts and journal entries. Attempt cross-tenant parent and journal line references — all must be rejected. Same-tenant parent and journal line references must succeed.

### Tests for User Story 1 + User Story 2 (required per FR-009)

> Tests are written FIRST and MUST FAIL before implementation. After implementation they MUST PASS.

- [X] T005 [P] [US1] Write test `test_cross_tenant_parent_account_rejected` in `backend/apps/accounting/tests/test_accounting_api.py` — create Tenant A and Tenant B accounts, then as Tenant A POST a child account with Tenant B's account as parent_id. Assert 400 and no child account created.

- [X] T006 [P] [US1] Write test `test_cross_tenant_journal_line_rejected` in `backend/apps/accounting/tests/test_accounting_api.py` — create accounts in Tenant A and Tenant B, then as Tenant A POST a journal entry with a line referencing Tenant B's account. Assert 400 and no journal entry or line saved.

- [X] T007 [P] [US1] Write test `test_mixed_tenant_journal_entry_rejected` in `backend/apps/accounting/tests/test_accounting_api.py` — POST a journal entry with one valid Tenant A account and one Tenant B account in the same entry. Assert 400 and verify both tenants' entry counts, balances, ledgers, and report totals remain unchanged.

- [X] T008 [P] [US1] Write test `test_cross_tenant_no_side_effects` in `backend/apps/accounting/tests/test_accounting_api.py` — verify that after a rejected cross-tenant attempt, neither tenant's account hierarchy, journal entry list, ledger, or trial balance is altered.

- [X] T009 [P] [US2] Verify existing `test_accounts_isolated_between_tenants`, `test_journal_entries_isolated_between_tenants`, and `test_cross_tenant_account_not_accessible` tests still pass unchanged (already exist at lines 950-1053). Do not modify these tests.

- [X] T010 [P] [US2] Write test `test_same_tenant_child_account_after_isolation` in `backend/apps/accounting/tests/test_accounting_api.py` — after the isolation fix, create a parent and child account in the same tenant. Assert 201 and the child correctly references the parent.

- [X] T011 [P] [US2] Write test `test_same_tenant_journal_entry_after_isolation` in `backend/apps/accounting/tests/test_accounting_api.py` — after the isolation fix, create a balanced journal entry using only same-tenant accounts. Assert 201 and the entry is retrievable.

### Implementation for User Story 1 + User Story 2

- [X] T012 [US1] Fix `AccountSerializer.validate_parent_id` in `backend/apps/accounting/serializers.py` — replace `models.Account.objects.get(pk=value)` with `models.Account.objects.for_tenant(tenant_id).get(pk=value)` using the tenant_id from serializer context. The "does not exist" branch already raises ValidationError — no change needed for the error message.

- [X] T013 [US1] Fix `JournalEntryLineSerializer.account_id` field in `backend/apps/accounting/serializers.py` — override `__init__` to set `self.fields['account_id'].queryset = models.Account.objects.for_tenant(request.tenant_id)` so that DRF's PrimaryKeyRelatedField validation only accepts same-tenant accounts.

- [X] T014 [US2] Verify `AccountSerializer.get_children` at line 26 in `backend/apps/accounting/serializers.py` — confirm the children queryset uses the same parent FK which is already tenant-scoped via the parent account (no change needed, just verify).

- [X] T015 [US2] Verify `JournalEntrySerializer.validate` at line 119 in `backend/apps/accounting/serializers.py` — confirm the imbalance check and zero-amount check remain unchanged and still apply to tenant-scoped lines (no change needed, just verify).

- [X] T016 [US1] Run the new tests from T005–T011 to confirm they pass after the serializer fixes:
      `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/accounting/tests/test_accounting_api.py::MultiTenantIsolationTests -v`

**Checkpoint**: At this point, the P0 tenant isolation gap is closed. Cross-tenant account references are rejected, same-tenant workflows succeed, and regression tests prove the property.

---

## Phase 4: User Story 3 — Provide Safe Rejection Feedback (Priority: P2)

**Goal**: Ensure error messages for inaccessible account references are consistent, safe, and do not disclose whether another tenant's records exist.

**Independent Test**: Submit accounting records with unknown, inaccessible, and cross-tenant account identifiers. Each failure is reported with the same error behavior and does not expose tenant-specific account details.

### Tests for User Story 3

- [X] T017 [P] [US3] Write test `test_inaccessible_account_error_safe` in `backend/apps/accounting/tests/test_accounting_api.py` — submit requests with an unknown UUID, a cross-tenant UUID, and a malformed UUID. Assert all produce the same error response format without disclosing account name, type, or tenant.

### Implementation for User Story 3

- [X] T018 [US3] Review the error message in `AccountSerializer.validate_parent_id` at line 36 of `backend/apps/accounting/serializers.py` — ensure the ValidationError message does not reveal whether the parent_id exists or belongs to another tenant. The current message `f"Parent account with id {value} does not exist."` is acceptable for all failure cases (unknown, invalid, or inaccessible).

- [X] T019 [US3] Review the error message produced by `JournalEntryLineSerializer` when `account_id` fails PrimaryKeyRelatedField validation — ensure it does not reveal whether the account exists or belongs to another tenant. DRF's default "Invalid pk" message is acceptable. No custom message required.

- [X] T020 [US3] Run all accounting tests to confirm US3 tests pass alongside US1/US2 tests:
      `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/accounting/tests/ -v`

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation updates, and quality assurance

- [X] T021 Run the full backend test suite to confirm no regressions:
      `cd backend; $env:DJANGO_SETTINGS_MODULE='config.settings.test'; py -m pytest apps/accounts/tests/ apps/accounting/tests/ -v`

- [X] T022 [P] Update `AGENTS.md` to mark this feature's current phase as "IMPLEMENTATION COMPLETE" after all tasks pass

- [X] T023 [P] Run through each scenario in `specs/008-p0-tenant-isolation/quickstart.md` to validate end-to-end behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify existing state
- **Foundational (Phase 2)**: Depends on Setup
- **US1 + US2 (Phase 3)**: Depends on Phase 2 — Core fixes and regression tests
- **US3 (Phase 4)**: Depends on Phase 3 — Error refinement after the core isolation fix is in place
- **Polish (Phase 5)**: Depends on all phases being complete

### User Story Dependencies

- **User Story 1 (P1) + User Story 2 (P1)**: Same implementation surface — scoped together in one phase
- **User Story 3 (P2)**: Depends on the core fix from US1/US2 being in place

### Within Each Phase

- Tests (where included) MUST be written and FAIL before implementation
- Implementation before refinement
- Verification before moving to next phase

### Parallel Opportunities

- T001, T002, T003 can run in parallel (reading code + running tests)
- T005–T011 (all tests) can run in parallel within Phase 3
- T022 and T023 can run in parallel within Phase 5

---

## Parallel Example: Phase 3 (US1 + US2)

```bash
# Launch all tests for US1 + US2 together:
Task: "Write test_cross_tenant_parent_account_rejected"
Task: "Write test_cross_tenant_journal_line_rejected"
Task: "Write test_mixed_tenant_journal_entry_rejected"
Task: "Write test_cross_tenant_no_side_effects"
Task: "Write test_same_tenant_child_account_after_isolation"
Task: "Write test_same_tenant_journal_entry_after_isolation"

# Implementation (serial only — both fixes in same file):
Task: "Fix validate_parent_id in serializers.py"
Task: "Fix JournalEntryLineSerializer account_id queryset"
```

---

## Implementation Strategy

### MVP First (Phase 3 Only)

1. Complete Phase 1: Setup (read code, verify tests)
2. Complete Phase 2: Foundational (tenant context)
3. Complete Phase 3: US1 + US2
   - Write all 7 tests first (T005–T011) — they should FAIL
   - Implement the two serializer fixes (T012, T013) — tests should now PASS
   - Verify existing tests still pass (T009)
4. **STOP AND VALIDATE**: The P0 blocker is closed at this point
5. Deploy/demo if needed

### Incremental Delivery

1. Phase 1–3 → P0 fix complete (MVP)
2. Phase 4 → Safe error refinement (P2)
3. Phase 5 → Verification and documentation

---

## Notes

- No new dependencies, no schema migrations, no new models
- All changes stay within `backend/apps/accounting/serializers.py` and `backend/apps/accounting/tests/test_accounting_api.py`
- Tests are REQUIRED per spec FR-009 — write them before implementation
- [P] tasks = different files, no dependencies
- Commit after each logical group
