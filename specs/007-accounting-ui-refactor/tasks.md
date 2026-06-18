---
description: "Task list for Accounting UI Refactor feature implementation"
---

# Tasks: Accounting UI Refactor

**Input**: Design documents from `specs/007-accounting-ui-refactor/`

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

**Purpose**: Create directory structure, shared UI primitives, service layer, and shared hook

- [X] T001 Create directory structure at `frontend/src/components/accounting/{accounts,journal,ledger,reports}/`, `frontend/src/components/shared/`, `frontend/src/hooks/`, `frontend/src/services/`, `frontend/src/pages/accounting/`
- [X] T002 [P] Create `Button.jsx` shared component at `frontend/src/components/shared/Button.jsx` — renders `<button>` with variant prop (primary, secondary, danger), accepts disabled, onClick, children, style override
- [X] T003 [P] Create `Input.jsx` shared component at `frontend/src/components/shared/Input.jsx` — renders `<input>` with label prop, error prop for inline validation, accepts all standard input props
- [X] T004 [P] Create `Modal.jsx` shared component at `frontend/src/components/shared/Modal.jsx` — renders overlay + centered card with title, children, onClose, footer actions; closes on overlay click and Escape key
- [X] T005 [P] Create `Table.jsx` shared component at `frontend/src/components/shared/Table.jsx` — renders `<table>` with columns config array (key, label, render?), data array, optional footer; handles empty state
- [X] T006 [P] Create `accountingService.js` at `frontend/src/services/accountingService.js` — centralized service object with methods: getAccounts, createAccount, updateAccount, deleteAccount, getJournalEntries, createJournalEntry, postJournalEntry, getLedger, getTrialBalance, getIncomeStatement, getBalanceSheet; each wraps `api.get/post` with correct paths
- [X] T007 [P] Create `useAccounting.js` hook at `frontend/src/hooks/useAccounting.js` — manages accounts list state, loading, error; exposes fetchAccounts, accounts, loading, error

---

## Phase 2: User Story 1 — Chart of Accounts (Priority: P1) 🎯 MVP

**Goal**: Refactor account components into `accounts/` subdirectory and extract CreateAccountModal. Page structure matches spec FR-001 (domain subdirectories).

**Independent Test**: Navigate to `/accounting/accounts`, expand tree nodes, create/edit/deactivate accounts. Verify all old ChartOfAccountsPage functionality works via AccountsPage using CreateAccountModal.

### Implementation for US1

- [X] T008 [P] [US1] Move `AccountRow.jsx` to `frontend/src/components/accounting/accounts/AccountRow.jsx` — update imports if needed, keep recursive tree logic unchanged
- [X] T009 [P] [US1] Move `AccountTree.jsx` to `frontend/src/components/accounting/accounts/AccountTree.jsx` — update import path for AccountRow
- [X] T010 [US1] Create `CreateAccountModal.jsx` at `frontend/src/components/accounting/accounts/CreateAccountModal.jsx` — extract inline modal from ChartOfAccountsPage; props: open, onClose, account (null=create), accounts list (for parent selector), onSaved callback; uses shared Modal, Input, Button
- [X] T011 [US1] Create `AccountsPage.jsx` at `frontend/src/pages/accounting/AccountsPage.jsx` — port ChartOfAccountsPage to new structure; import AccountTree, CreateAccountModal; use accountingService for API calls; use useAccounting for shared state (or local fetch for independence); remove inline modal/button/input styles in favor of shared components

**Checkpoint**: US1 complete — accounts page fully functional independently at new path

---

## Phase 3: User Story 2 — Journal Entry (Priority: P1)

**Goal**: Refactor journal components into `journal/` subdirectory, extract JournalEntryForm, merge form and list into single JournalPage.

**Independent Test**: Navigate to `/accounting/journal`, create a balanced journal entry, verify it appears in the list below the form. Post it and verify lock.

### Implementation for US2

- [X] T012 [P] [US2] Move `AccountSelect.jsx` to `frontend/src/components/accounting/journal/AccountSelect.jsx` — update import path for accountingService
- [X] T013 [P] [US2] Move `JournalLineRow.jsx` to `frontend/src/components/accounting/journal/JournalLineRow.jsx` — update import path for AccountSelect
- [X] T014 [US2] Create `JournalEntryForm.jsx` at `frontend/src/components/accounting/journal/JournalEntryForm.jsx` — extract form from JournalEntryFormPage; props: onSaved callback; manages lines, date, description, reference state internally; shows balance bar; uses shared Button for submit/cancel; uses JournalLineRow; uses useAccounting for accounts list
- [X] T015 [US2] Create `JournalPage.jsx` at `frontend/src/pages/accounting/JournalPage.jsx` — combines JournalEntryForm at top and journal entries list below; fetches entries using accountingService; supports date range filters; uses shared Table or inline list
- [X] T016 [US2] Remove old `JournalEntryFormPage.jsx` and `JournalEntriesPage.jsx` from `frontend/src/pages/`

**Checkpoint**: US2 complete — journal page fully functional independently at new path

---

## Phase 4: User Story 3 — Ledger View (Priority: P2)

**Goal**: Move ledger components into `ledger/` subdirectory and rename page.

**Independent Test**: Navigate to `/accounting/ledger/{accountId}`, verify running balance, date filters, and totals footer.

### Implementation for US3

- [X] T017 [P] [US3] Move `LedgerTable.jsx` to `frontend/src/components/accounting/ledger/LedgerTable.jsx` — optionally refactor to use shared Table component
- [X] T018 [US3] Create `LedgerPage.jsx` at `frontend/src/pages/accounting/LedgerPage.jsx` — port from existing `pages/LedgerPage.jsx`; update imports; use accountingService for ledger fetch; optionally use shared Input and Button for filter controls
- [X] T019 [P] [US3] Remove old `LedgerPage.jsx` and `LedgerTable.jsx` from old locations

**Checkpoint**: US3 complete — ledger view functional independently at new path

---

## Phase 5: User Story 4 — Financial Reports (Priority: P2)

**Goal**: Move report components into `reports/` subdirectory and rename page.

**Independent Test**: Navigate to `/accounting/reports`, generate Trial Balance, Income Statement, Balance Sheet. Verify all three render correctly.

### Implementation for US4

- [X] T020 [P] [US4] Move `ReportSelector.jsx` to `frontend/src/components/accounting/reports/ReportSelector.jsx` — optionally refactor to use shared Button and Input components
- [X] T021 [P] [US4] Move `ReportTable.jsx` to `frontend/src/components/accounting/reports/ReportTable.jsx` — optionally refactor to use shared Table component
- [X] T022 [US4] Create `ReportsPage.jsx` at `frontend/src/pages/accounting/ReportsPage.jsx` — port from existing `pages/ReportsPage.jsx`; update imports; optionally use shared components

**Checkpoint**: US4 complete — all three reports functional independently at new path

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Wire up routes, clean up old files, and validate end-to-end

- [X] T023 Update `App.jsx` routes: replace old page paths with new `pages/accounting/*` imports; keep route paths `/accounting/accounts`, `/accounting/journal`, `/accounting/ledger/:accountId`, `/accounting/reports`
- [X] T024 Remove old page files: `frontend/src/pages/ChartOfAccountsPage.jsx` (other old pages already removed in prior tasks)
- [X] T025 Run `cd frontend && npx vite build` to verify no compilation errors
- [X] T026 Run quickstart.md validation scenarios end-to-end and fix any issues found

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Setup — shared components needed for CreateAccountModal and AccountsPage
- **US2 (Phase 3)**: Depends on Setup — shared components and accountingService needed
- **US3 (Phase 4)**: Depends on Setup — shared Table/Button/Input optional but recommended
- **US4 (Phase 5)**: Depends on Setup — shared Table/Button/Input optional but recommended
- **Polish (Phase 6)**: Depends on all phases — needs all new pages in place before route update and cleanup

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — can proceed independently
- **US2 (P1)**: No dependencies on other stories — can proceed independently after Setup
- **US3 (P2)**: No dependencies on other stories — can proceed independently after Setup
- **US4 (P2)**: No dependencies on other stories — can proceed independently after Setup

### Parallel Opportunities

- T002-T007 (Setup phase) can all run in parallel
- T008, T009 (US1 moves) can run in parallel
- T012, T013 (US2 moves) can run in parallel
- T017 (US3 move) and T020, T021 (US4 moves) can all run in parallel
- US1, US2, US3, US4 can all proceed in parallel after Setup completes
- Final T022-T025 must run sequentially

---

## Parallel Example: Setup Phase

```bash
# Launch all shared component + service creation together:
Task: "Create Button component"
Task: "Create Input component"
Task: "Create Modal component"
Task: "Create Table component"
Task: "Create accountingService.js"
Task: "Create useAccounting.js"
```

## Parallel Example: User Stories

```bash
# Once Setup done, all stories can proceed:
Task: "US1 - Accounts page refactor"
Task: "US2 - Journal page refactor"
Task: "US3 - Ledger page refactor"
Task: "US4 - Reports page refactor"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (7 tasks)
2. Complete Phase 2: US1 — Accounts (4 tasks)
3. **STOP and VALIDATE**: Navigate chart of accounts, create/edit/deactivate accounts
4. Deploy/demo Accounts page as MVP increment

### Incremental Delivery

1. Setup + US1 → Accounts page refactored (MVP!)
2. Add US2 → Journal page refactored
3. Add US3 → Ledger page refactored
4. Add US4 → Reports page refactored
5. Polish → Route update, cleanup, validation

### Parallel Team Strategy

With multiple developers:
- Developer A: Phase 1 Setup (shared components + service + hook)
- Developer B: US1 (Accounts page refactor) — can start after shared components ready
- Developer C: US2 (Journal page refactor) — can start after accountingService ready
- Once Setup done, Developer A can take US3/US4

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- The existing components already work — this is a pure refactoring (move + extract + rename)
- No backend changes required — all endpoints already exist from feature 006
- Commit after each phase or logical group to maintain clean history
