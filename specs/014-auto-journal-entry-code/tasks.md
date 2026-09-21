# Tasks: Auto Journal Entry Code

**Input**: Design documents from `/specs/014-auto-journal-entry-code/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: New backend mint tests act as verification gates (`backend/apps/accounting/tests/test_auto_journal_entry_code.py`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/apps/accounting/`, `frontend/src/`
- Paths below are repo-relative per plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm toolchains run before any story work

- [x] T001 Verify backend test toolchain runs in backend/ (`DJANGO_SETTINGS_MODULE=config.settings.test`) — 403 passed, 1 skipped baseline
- [x] T002 [P] Verify frontend toolchain builds in frontend/ (`npm run build`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Authoritative backend mint path confirmed green — MUST complete before ANY user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Tenant-scoped next-reference helper with year scoping and collision-skip added to `JournalEntryService` in `backend/apps/accounting/services.py` (`next_reference()`, format `JE-YYYY-NNNN`)
- [x] T004 `create_entry()` accepts an optional/blank reference and mints when absent in `backend/apps/accounting/services.py`
- [x] T005 Serializer accepts blank/missing reference on create (no code-required rejection) in `backend/apps/accounting/serializers.py`
- [x] T006 Create view returns 201 with minted reference in `backend/apps/accounting/views.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create a journal entry with an auto-generated code (Priority: P1) 🎯 MVP

**Goal**: Create form shows a disabled Reference preview (`JE-2026-0001`, +1 per saved entry); saving without typing a code succeeds with the shown (or next free) code and no "code required" error

**Independent Test**: Open create form (reference visible, not editable) → save with date + description + 2 lines → saved entry carries the shown code; reopen shows the next code

### Implementation for User Story 1

- [x] T007 [P] [US1] Contract check: POST without reference returns 201 with minted reference (`test_post_without_reference_mints_next`)
- [x] T008 [P] [US1] Add `GET /accounting/journal-entries/next-reference/` preview endpoint in `backend/apps/accounting/views.py`
- [x] T009 [P] [US1] Add `getNextJournalReference()` to `frontend/src/services/accountingService.js`
- [x] T010 [US1] Replace editable Reference field with disabled preview in `frontend/src/components/accounting/journal/JournalEntryForm.jsx` (depends on T009)
- [x] T011 [US1] Keep reference out of the create payload in `frontend/src/components/accounting/journal/JournalEntryForm.jsx` (depends on T010)

---

## Phase 4: User Story 2 - Codes increment by 1 per save (Priority: P2)

**Goal**: Each save mints the next sequential code from the highest existing suffix for that business and year

**Independent Test**: Create several entries in a row; each code increments by exactly 1 (`JE-2026-0001`, `JE-2026-0002`, `JE-2026-0003`)

### Implementation for User Story 2

- [x] T012 [P] [US2] Sequence increments and skips collisions (`test_second_post_without_reference_increments`, `test_collision_skips_taken_reference`, `test_manual_high_reference_then_mint_continues_after_it`)
- [x] T013 [P] [US2] Gaps from deleted drafts are not reused (max-suffix + collision-skip loop in `next_reference()`)

---

## Phase 5: User Story 3 - Code is preserved and read-only after creation (Priority: P3)

**Goal**: Once an entry exists, its code is shown but can never be edited — draft or posted

**Independent Test**: Edit an existing entry's description/lines and confirm the code is unchanged

### Implementation for User Story 3

- [x] T014 [P] [US3] Journal entries remain immutable (existing 405 on PUT/PATCH/DELETE in `backend/apps/accounting/views.py` — unchanged by this feature)
- [x] T015 [P] [US3] Reference field is non-editable in the saved-draft state in `frontend/src/components/accounting/journal/JournalEntryForm.jsx`

---

## Phase 6: User Story 4 - Preview resolves to next available code (Priority: P4)

**Goal**: Opening the create form multiple times without saving never consumes or skips codes; a stale preview still saves successfully with the next free code

**Independent Test**: Open the form, cancel, reopen, save → the entry gets `JE-2026-0002` (not `JE-2026-0003`)

### Implementation for User Story 4

- [x] T016 [P] [US4] Preview endpoint is read-only and consumes nothing (`test_next_reference_endpoint_returns_preview_without_consuming`)
- [x] T017 [P] [US4] Stale preview falls through to the next free code at save (`test_stale_preview_save_gets_next_free_reference`)
- [x] T018 [P] [US4] Cross-tenant sequences stay independent (`test_cross_tenant_references_use_independent_sequences`)

---

## Phase 7: Verification

- [x] T019 Full backend suite green (`py -m pytest apps/ -q` → 421 passed, 1 skipped)
- [x] T020 [P] Migrations clean (`py manage.py makemigrations --check --dry-run` → No changes detected)
- [x] T021 [P] Frontend build green (`npm run build`)
- [x] T022 [P] Frontend lint at baseline (`npm run lint` → 18 problems, zero new)
