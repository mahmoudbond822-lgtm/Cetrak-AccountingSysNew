---
description: "Task list for Accounting Frontend feature implementation"
---

# Tasks: Accounting Frontend

**Input**: Design documents from `specs/006-accounting-frontend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested — skip test tasks; validate via quickstart.md scenarios

**Organization**: Tasks grouped by user story for independent implementation

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to user story (US1, US2, US3, US4)
- Include exact file paths

## Path Conventions

- **Backend**: `backend/apps/accounting/`
- **Frontend**: `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create common structure and navigation shared across all accounting pages

- [X] T001 Create `frontend/src/components/accounting/` directory structure
- [X] T002 [P] Create AccountingNav shared navigation component at `frontend/src/components/Layout/AccountingNav.jsx`
- [X] T003 [P] Add accounting route definitions to `frontend/src/App.jsx` (routes to all 6 accounting pages)

---

## Phase 2: Foundational (Backend Blocking Prerequisites)

**Purpose**: Backend additions required by US2, US3, and US4 — accounts API (US1) already exists

**⚠️ CRITICAL**: US2, US3, US4 depend on this phase; US1 can proceed in parallel

- [X] T004 Route JournalEntryViewSet in `backend/apps/accounting/urls.py` (add import + router.register for journal-entries)
- [X] T005 [P] Create `CanViewReports` permission class at `backend/apps/accounting/permissions.py` (allows Admin, Accountant, Manager roles)
- [X] T006 [P] Create `LedgerService` with `get_ledger(account_id, date_from, date_to)` method in `backend/apps/accounting/services.py` — query JournalEntryLine ordered by entry__date, compute running balance in Python
- [X] T007 [P] Create `ReportService` with `trial_balance(date_from, date_to)`, `income_statement(date_from, date_to)`, `balance_sheet(as_of)` methods in `backend/apps/accounting/services.py` — use ORM aggregation
- [X] T008 [P] Create LedgerSerializer and Report serializers in `backend/apps/accounting/serializers.py`
- [X] T009 Create LedgerViewSet and ReportViewSet (trial-balance, income-statement, balance-sheet actions) in `backend/apps/accounting/views.py`
- [X] T010 Add Ledger and Report URL routing to `backend/apps/accounting/urls.py`

**Checkpoint**: All backend APIs ready — accounts, journal entries, ledger, reports

---

## Phase 3: User Story 1 — Chart of Accounts (Priority: P1) 🎯 MVP

**Goal**: Accountants can view the hierarchical chart of accounts, create/edit/deactivate accounts

**Independent Test**: Login as accountant, navigate to `/accounting/accounts`, expand tree nodes, create a new account, edit it, and deactivate it

### Implementation for US1

- [X] T011 [P] [US1] Create `AccountRow` component at `frontend/src/components/accounting/AccountRow.jsx` — displays account name, type, expand/collapse toggle for children
- [X] T012 [P] [US1] Create `AccountTree` component at `frontend/src/components/accounting/AccountTree.jsx` — renders recursive tree from API response using AccountRow, handles expand/collapse state
- [X] T013 [US1] Create `ChartOfAccountsPage` at `frontend/src/pages/ChartOfAccountsPage.jsx` — fetches accounts from `GET /api/v1/accounting/accounts/?tree=true`, displays AccountTree, skeleton loader while loading, error handling
- [X] T014 [US1] Add create/edit account form (inline modal or dedicated section) to `ChartOfAccountsPage.jsx` — fields: name, type dropdown, optional parent selector, description; calls `POST /api/v1/accounting/accounts/` or `PATCH /api/v1/accounting/accounts/{id}/`
- [X] T015 [US1] Add deactivate account action to `ChartOfAccountsPage.jsx` — confirm dialog, calls `DELETE /api/v1/accounting/accounts/{id}/`, removes from tree on success

**Checkpoint**: US1 complete — chart of accounts fully functional independently

---

## Phase 4: User Story 2 — Journal Entry Creation & Posting (Priority: P1)

**Goal**: Accountants can create balanced journal entries with multiple lines, and post them (locking edits)

**Independent Test**: Create a journal entry with two lines (Dr 1000, Cr 1000), verify balance indicator shows "balanced", post it, verify list shows locked entry

### Implementation for US2

- [X] T016 [P] [US2] Create `AccountSelect` component at `frontend/src/components/accounting/AccountSelect.jsx` — searchable dropdown that fetches accounts from `GET /api/v1/accounting/accounts/`, allows filtering by name
- [X] T017 [P] [US2] Create `JournalLineRow` component at `frontend/src/components/accounting/JournalLineRow.jsx` — displays account selector, debit input, credit input, description, remove button; validates single-field (debit XOR credit)
- [X] T018 [US2] Create `JournalEntryFormPage` at `frontend/src/pages/JournalEntryFormPage.jsx` — date picker, description, reference fields; dynamic list of JournalLineRows; real-time balance calculation (total debit vs total credit); submit calls `POST /api/v1/accounting/journal-entries/`; disabled submit when imbalanced or <2 lines
- [X] T019 [P] [US2] Create `JournalEntriesPage` at `frontend/src/pages/JournalEntriesPage.jsx` — lists journal entries from `GET /api/v1/accounting/journal-entries/` with date range filters; each entry shows reference, date, description, totals, line count; link to create new
- [X] T020 [US2] Add Post action to journal entry detail view — calls `POST /api/v1/accounting/journal-entries/{id}/post/` (add this endpoint to backend viewset if missing)

**Checkpoint**: US2 complete — journal entries can be created, validated, posted, and listed

---

## Phase 5: User Story 3 — Ledger View (Priority: P2)

**Goal**: Accountants can view transactions for any account with running balance

**Independent Test**: Select an account with posted entries, navigate to `/accounting/ledger/{accountId}`, verify date-sorted rows with correct running balance

### Implementation for US3

- [X] T021 [P] [US3] Create `LedgerTable` component at `frontend/src/components/accounting/LedgerTable.jsx` — displays columns: Date, Description, Reference, Debit, Credit, Running Balance
- [X] T022 [US3] Create `LedgerPage` at `frontend/src/pages/LedgerPage.jsx` — takes `accountId` from URL params, fetches ledger from `GET /api/v1/accounting/ledger/?account_id={id}`, displays LedgerTable with account info header, date range filter, totals footer

**Checkpoint**: US3 complete — ledger view functional independently

---

## Phase 6: User Story 4 — Financial Reports (Priority: P2)

**Goal**: Managers can generate Trial Balance, Income Statement, and Balance Sheet reports

**Independent Test**: Select report type Trial Balance with a date range, verify all accounts with balances appear and total debits = total credits

### Implementation for US4

- [X] T023 [P] [US4] Create `ReportSelector` component at `frontend/src/components/accounting/ReportSelector.jsx` — dropdown for report type (Trial Balance, Income Statement, Balance Sheet), date range inputs (from/to for P&L, as_of for balance sheet)
- [X] T024 [P] [US4] Create `ReportTable` component at `frontend/src/components/accounting/ReportTable.jsx` — renders report rows with account name, type, debit/credit columns; handles all three report shapes (TB, IS, BS)
- [X] T025 [US4] Create `ReportsPage` at `frontend/src/pages/ReportsPage.jsx` — fetches selected report from `GET /api/v1/accounting/reports/{type}/` with query params, displays via ReportTable and ReportSelector; handles empty/no-data state

**Checkpoint**: US4 complete — all three reports functional independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, error handling, validation improvements

- [X] T026 Handle loading and empty states across all pages (skeleton loaders, empty messages, error toasts)
- [X] T027 Verify all forms disable submit during API calls and show inline field errors
- [X] T028 Add confirmation dialogs for destructive actions (deactivate account, unapplied form navigation)
- [X] T029 Run quickstart.md validation scenarios end-to-end and fix any issues
- [X] T030 Run `cd backend && py -m pytest apps/accounting/tests/ -v` to verify no backend regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US2, US3, US4
- **US1 (Phase 3)**: Can start after Setup — **no dependency on Backend Foundational** (accounts API already exists)
- **US2 (Phase 4)**: Depends on Foundational (T004 — JournalEntryViewSet routing)
- **US3 (Phase 5)**: Depends on Foundational (T006, T009 — Ledger backend endpoint)
- **US4 (Phase 6)**: Depends on Foundational (T007, T009 — Report backend endpoints)
- **Polish (Phase 7)**: Depends on US1, US2 completion at minimum

### User Story Dependencies

- **US1 (P1)**: No backend dependencies — existing Accounts API is sufficient
- **US2 (P1)**: Depends on T004 (route JournalEntryViewSet)
- **US3 (P2)**: Depends on new Ledger backend (T006, T009)
- **US4 (P2)**: Depends on new Report backend (T007, T009)

### Parallel Opportunities

- T001, T002, T003 (Setup) can all run in parallel
- T005, T006, T007, T008 (Foundational) can run in parallel
- T011, T012 (US1 components) can run in parallel
- T016, T017 (US2 components) can run in parallel
- T021 (US3) and T023, T024 (US4) can run in parallel once T006, T007 are done
- US1 is fully independent of all other stories — can be done simultaneously

---

## Parallel Example: User Story 1

```bash
# Launch all UI components together:
Task: "Create AccountRow component"
Task: "Create AccountTree component"
```

## Parallel Example: Foundational Backend

```bash
# Launch all backend additions together:
Task: "Route JournalEntryViewSet in urls.py"
Task: "Create CanViewReports permission"
Task: "Create LedgerService"
Task: "Create ReportService"
Task: "Create Ledger and Report serializers"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (3 tasks)
2. Complete Phase 3: US1 — Chart of Accounts (5 tasks)
3. **STOP and VALIDATE**: Navigate chart of accounts, create/edit/deactivate accounts
4. Deploy/demo Chart of Accounts as MVP increment

### Incremental Delivery

1. Setup + US1 → Chart of Accounts (MVP!)
2. Add Foundational backend → All APIs ready
3. Add US2 → Journal Entry creation/posting
4. Add US3 → Ledger view
5. Add US4 → Financial reports
6. Polish → Production-ready

### Parallel Team Strategy

With multiple developers:
- Developer A: US1 (Chart of Accounts) — can start immediately after Setup
- Developer B: Phase 2 (Foundational backend) — required by US2/3/4
- Developer C: US2 components (AccountSelect, JournalLineRow) — can start once T004 done
- Once Foundational done: B/C can do US3 and US4
