---

description: "Task list for Accounting Schema implementation"

---

# Tasks: Accounting Schema

**Input**: Design documents from `specs/005-accounting-schema/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are not requested — this feature focuses on schema and service-layer implementation. The existing 36 tests serve as the regression safety net.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` at repository root
- **Frontend**: Not affected by this feature

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Foundational model layer that all user stories depend on.

- [X] T001 Create Account, JournalEntry, and JournalEntryLine models in `backend/apps/accounting/models.py` (per data-model.md: Account with parent_id, type enum, is_active; JournalEntry with date/description/reference; JournalEntryLine with debit/credit amounts and FK to Account)
- [X] T002 Generate initial migration for the accounting app in `backend/apps/accounting/migrations/`

**Checkpoint**: Shared infrastructure ready — all three entities exist with proper fields, relationships, and migration.

---

## Phase 2: User Story 1 — Chart of Accounts (Priority: P1)

**Goal**: An accountant can create, organize, and view the chart of accounts as a hierarchical tree. Accounts have a parent-child structure and are typed (Asset, Liability, Equity, Revenue, Expense).

**Independent Test**: An authenticated admin user creates two accounts (a root Asset account and a child Cash account), then fetches the tree and sees the parent-child nesting.

### Implementation for User Story 1

- [X] T003 [P] [US1] Create AccountSerializer in `backend/apps/accounting/serializers.py` — supports create/list/tree, validates type enum, parent_id existence, and tree depth limit
- [X] T004 [P] [US1] Create AccountingPermission in `backend/apps/accounting/permissions.py` — allows Admin and Accountant roles for accounting operations
- [X] T005 [US1] Create AccountingService with account CRUD logic in `backend/apps/accounting/services.py` — create_account with validation, list_accounts (flat + tree via recursive CTE), get_account, deactivate_account
- [X] T006 [US1] Create AccountViewSet in `backend/apps/accounting/views.py` — GET/POST /accounts/, GET /accounts/{id}/, GET /accounts/?tree=true
- [X] T007 [US1] Create URL configuration in `backend/apps/accounting/urls.py` — route /api/v1/accounting/accounts/ to AccountViewSet

**Checkpoint**: US1 complete — accounts can be created, organized hierarchically, and viewed as a tree. Tenant isolation is enforced via existing middleware.

---

## Phase 3: User Story 2 — Journal Entries (Priority: P1)

**Goal**: An accountant can record financial transactions as journal entries with balanced debits and credits. The system rejects unbalanced entries with a clear error.

**Independent Test**: An authenticated admin user creates a journal entry with two lines (debit 1000 to Cash, credit 1000 to Revenue) and receives 201. The same user then attempts an unbalanced entry (debit 1000, credit 500) and receives 400.

### Implementation for User Story 2

- [X] T008 [P] [US2] Create JournalEntrySerializer and JournalEntryLineSerializer in `backend/apps/accounting/serializers.py` — inline lines on create, validates balanced-entry rule, non-negative amounts, single-field debit/credit, at least 2 lines, not all zero amounts
- [X] T009 [US2] Create JournalEntryService in `backend/apps/accounting/services.py` — create_journal_entry with full validation (balanced, accounts exist, tenant match), list_entries with date range filtering, get_entry_detail
- [X] T010 [US2] Create JournalEntryViewSet in `backend/apps/accounting/views.py` — GET/POST /journal-entries/, GET /journal-entries/{id}/ (no update or delete — entries are immutable)
- [X] T011 [US2] Generate and apply the DB CHECK constraint migration for the balanced-entry rule in `backend/apps/accounting/migrations/` — PostgreSQL function `check_entry_balanced()` + CHECK constraint on `accounting_journalentry` table

**Checkpoint**: US2 complete — journal entries can be created with balanced lines. Unbalanced entries are rejected. Tenant isolation is enforced.

---

## Phase 4: User Story 3 — Data Integrity Enforcement (Priority: P1)

**Goal**: Accounting data integrity is guaranteed at the application layer. Accounts used in journal entries cannot be deleted or have their type changed. Journal entries are immutable after creation.

**Independent Test**: A user creates a journal entry referencing an account, then attempts to delete or change the type of that account — both are rejected. A user attempts to PATCH or DELETE a journal entry — both are rejected.

### Implementation for User Story 3

- [X] T012 [P] [US3] Add model-level `clean()` validation on JournalEntry in `backend/apps/accounting/models.py` — validates balanced entry, zero-amount rejection, single-field debit/credit exclusivity
- [X] T013 [P] [US3] Add account locking logic in `backend/apps/accounting/services.py` — prevent account deletion if children exist (FR-003); prevent account deletion or type change if referenced by any JournalEntryLine (FR-004); soft-deactivation via is_active instead of hard delete
- [X] T014 [US3] Add immutability enforcement on JournalEntryViewSet in `backend/apps/accounting/views.py` — explicitly disable PUT, PATCH, DELETE methods; add permission class that denies modification to existing entries

**Checkpoint**: US3 complete — all data integrity rules are enforced. Accounts are locked after use. Journal entries are append-only.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Integration wiring and verification.

- [X] T015 Register accounting URLs in `backend/config/urls.py` — add path inclusion for `apps/accounting/urls` under `api/v1/accounting/`
- [X] T016 Run existing test suite to verify 36 tests still pass: `cd backend && py -m pytest apps/accounts/tests/ -v`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — foundation for all stories
- **User Story 1 (Phase 2)**: Depends on Setup (T001–T002) for Account model
- **User Story 2 (Phase 3)**: Depends on Setup (T001–T002) for JournalEntry and JournalEntryLine models; independent of US1 service layer (uses models directly)
- **User Story 3 (Phase 4)**: Depends on Setup for all models; depends on US1 for account service logic; depends on US2 for journal entry service logic
- **Polish (Phase 5)**: Depends on all phases being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Setup (models for Account)
- **User Story 2 (P1)**: Depends on Setup (models for JournalEntry, JournalEntryLine, Account)
- US1 and US2 service/serializer/view layers can run in parallel — they touch different files within the same app
- **User Story 3 (P1)**: Depends on both US1 and US2 (adds locking/immutability on top of existing code)

### Within Each User Story

- Services before serializers before views
- Views depend on serializers and permissions
- Models/config before migrations

### Parallel Opportunities

- All [P] tasks within a story can run in parallel (different files)
- T003, T004, T005 can run in parallel (serializers.py, permissions.py, services.py)
- T008, T009 can run in parallel (serializers.py, services.py)
- T012, T013 can run in parallel (models.py, services.py)
- Phase 2 (US1) and Phase 3 (US2) can run in parallel — they touch different views/serializers

---

## Parallel Example: Phase 2 + Phase 3

```bash
# Phase 2 — US1 service + serializer + permission (parallel):
Task: T003 [P] [US1] AccountSerializer in serializers.py
Task: T004 [P] [US1] AccountingPermission in permissions.py
Task: T005 [US1] AccountingService in services.py

# Then sequential within US1:
Task: T006 [US1] AccountViewSet in views.py
Task: T007 [US1] URLs

# Phase 3 — US2 can start after Phase 1 models are done:
Task: T008 [P] [US2] JournalEntrySerializer in serializers.py
Task: T009 [US2] JournalEntryService in services.py
Task: T010 [US2] JournalEntryViewSet in views.py
Task: T011 [US2] Balanced-entry CHECK constraint migration
```

---

## Implementation Strategy

### MVP First (Phase 2 + Phase 3)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: User Story 1 (T003–T007) — Chart of Accounts
3. Complete Phase 3: User Story 2 (T008–T011) — Journal Entries
4. **STOP and VALIDATE**: Manual test using Quickstart scenarios 1–3
5. Complete Phase 4: User Story 3 (T012–T014) — Data Integrity
6. **STOP and VALIDATE**: Quickstart scenario 4 (immutability)
7. Run regression suite (T016)
8. Deploy

### Incremental Delivery

1. Complete Phase 1 → Models exist, migration applied
2. Add US1 → Chart of Accounts → Deploy/Demo (accounts are non-functional without entries, but structure exists)
3. Add US2 → Journal Entries → Deploy/Demo (core accounting capability — MVP!)
4. Add US3 → Data Integrity → Deploy/Demo (hardening complete)

### Parallel Team Strategy

With multiple developers:

1. Phase 1 (Setup): Together — models in models.py
2. Once Setup is done:
   - Developer A: US1 Chart of Accounts (T003–T007)
   - Developer B: US2 Journal Entries (T008–T011)
3. Together: US3 Data Integrity (T012–T014) — depends on both stories
4. Together: Polish (T015–T016)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- The `apps/accounting/` directory already exists as a placeholder with only `__init__.py` — no directory creation needed
- Models extend `TenantScopedModel` from `apps.core.models` to inherit tenant scoping and UUID PK
- All monetary amounts use `DecimalField(max_digits=19, decimal_places=4)` per data-model.md
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
