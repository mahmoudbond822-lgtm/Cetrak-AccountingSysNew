# Tasks: Auto Invoice Number

**Input**: Design documents from `/specs/016-auto-invoice-number/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: New backend mint tests are written first as the verification gate (per-app `test_auto_invoice_number.py`, mirroring `test_auto_vendor_code.py`); all existing explicit-number invoice tests run unchanged as regression gates. T019 extends coverage only if the stale-preview path is uncovered.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Sales and purchase sides are symmetric — same-side tasks run sequentially, cross-side tasks in different files run in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/apps/sales/`, `backend/apps/purchases/`, `frontend/src/`
- Paths below are repo-relative per plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm toolchains run before any story work

- [X] T001 Verify backend test toolchain runs in backend/ (`DJANGO_SETTINGS_MODULE=config.settings.test`)
- [X] T002 [P] Verify frontend toolchain builds in frontend/ (`npm run build`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Authoritative backend mint paths for both invoice types — MUST complete before ANY user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Write failing sales mint tests first in backend/apps/sales/tests/test_auto_invoice_number.py (sequence INV-0001/INV-0002, blank-mint, locked-on-edit, cross-tenant independence, stale-preview, explicit-duplicate rejection)
- [X] T004 [P] Write failing purchase mint tests first in backend/apps/purchases/tests/test_auto_invoice_number.py (same matrix for purchase side)
- [X] T005 [P] Add SalesInvoiceService.next_number helper (INV- prefix, collision-skip, tenant-scoped) and blank→mint in create_draft in backend/apps/sales/services.py
- [X] T006 [P] Add PurchaseInvoiceService.next_number helper and blank→mint in create_draft in backend/apps/purchases/services.py
- [X] T007 [P] Accept blank/missing number on sales create (no number-required rejection) in backend/apps/sales/serializers.py
- [X] T008 [P] Accept blank/missing number on purchase create (no number-required rejection) in backend/apps/purchases/serializers.py
- [X] T009 Pass optional number through on sales create and stop passing number on sales update in backend/apps/sales/views.py (depends on T005, T007)
- [X] T010 Pass optional number through on purchase create and stop passing number on purchase update in backend/apps/purchases/views.py (depends on T006, T008)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create an invoice with an auto-generated number (Priority: P1) 🎯 MVP

**Goal**: Both create dialogs show a disabled Number preview (`INV-0001` per type, +1 per saved invoice of that type); saving without typing a number succeeds with the shown (or next free) number and no "number required" error

**Independent Test**: Open each create dialog (number visible, not editable) → save a valid invoice with lines → saved invoice carries the shown number; reopen shows the next number

### Implementation for User Story 1

- [X] T011 [P] [US1] Contract check sales: POST without number returns 201 with minted number per specs/016-auto-invoice-number/contracts/invoice-create.md (run backend/apps/sales/tests/test_auto_invoice_number.py)
- [X] T012 [P] [US1] Contract check purchase: POST without number returns 201 with minted number per specs/016-auto-invoice-number/contracts/invoice-create.md (run backend/apps/purchases/tests/test_auto_invoice_number.py)
- [X] T013 [P] [US1] Add disabled Number preview in create mode, keep number out of create payload, show read-only number on edit, and return saved invoice via onSaved in frontend/src/components/sales/invoices/InvoiceForm.jsx
- [X] T014 [P] [US1] Same dialog changes for purchase side in frontend/src/components/purchases/invoices/PurchaseInvoiceForm.jsx
- [X] T015 [US1] Add next-number preview helper, wire preview into form, and surface assigned-number note when save returns a different number in frontend/src/pages/sales/InvoicesPage.jsx (depends on T013)
- [X] T016 [US1] Same page changes for purchase side in frontend/src/pages/purchases/PurchaseInvoicesPage.jsx (depends on T014)
- [ ] T017 [US1] Manual browser walkthrough for both sides per specs/016-auto-invoice-number/quickstart.md (preview → save → list → reopen shows next) — PENDING human run; statically verified only, do not claim passed

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Numbers increment by 1 per saved invoice (Priority: P2)

**Goal**: Every saved invoice gets the next sequential number of its type (+1 from the highest existing number of that type); collisions skipped, per-type per-business sequences independent, gaps never reused

**Independent Test**: Create several invoices in a row per side → numbers run INV-0001, INV-0002, … with +1 each; sales and purchase sequences advance independently

### Implementation for User Story 2

- [X] T018 [P] [US2] Verify collision-skip, per-type independence, and cross-tenant tests in backend/apps/sales/tests/test_auto_invoice_number.py and backend/apps/purchases/tests/test_auto_invoice_number.py
- [X] T019 [US2] Cover stale-preview scenario per side (second save gets next free number plus note), extending the per-app test modules only where uncovered

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Number is locked after creation (Priority: P3)

**Goal**: Edit dialogs show the number read-only in draft and posted states; edits never blank, regenerate, or change it

**Independent Test**: Edit a draft invoice's dates/lines → number unchanged and not editable

### Implementation for User Story 3

- [X] T020 [US3] Verify edit dialogs show number read-only and saves preserve it in frontend/src/components/sales/invoices/InvoiceForm.jsx and frontend/src/components/purchases/invoices/PurchaseInvoiceForm.jsx
- [X] T021 [P] [US3] Verify locked-on-edit tests in backend/apps/sales/tests/test_auto_invoice_number.py and backend/apps/purchases/tests/test_auto_invoice_number.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full verification with no regressions

- [X] T022 Run full backend suite green in backend/ (`py -m pytest apps/ -q`, expect no regressions vs 381 passed / 1 skipped baseline)
- [X] T023 [P] Run frontend build plus lint with zero new problems in frontend/
- [X] T024 Confirm migration check clean in backend/ (`py manage.py makemigrations --check --dry-run`, expect "No changes detected")

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Mint path shared with US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Edit path independent of create preview

### Within Each User Story

- Contract/test verification before implementation changes
- Services before UI (UI preview depends on the mint contract holding)
- Sales and purchase sides are independent files — cross-side tasks run in parallel
- Same-side tasks run sequentially (service → serializer → view; form → page)
- Story complete before moving to next priority

### Parallel Opportunities

- T001 + T002 (separate toolchains, no shared files)
- T003 + T004 + T005 + T006 + T007 + T008 (six different files across both apps)
- T011 + T012 + T013 + T014 (contract checks vs dialog edits, four different files)
- T015 + T016 after their form tasks (different pages, no shared files)
- T018 + T021 (different verification targets, no shared files)
- T022 + T023 (backend suite vs frontend build/lint, independent)
- After Foundational, US1/US2/US3 can proceed in parallel if staffed

---

## Parallel Example: User Story 1

```bash
# Launch contract checks and dialog edits together (different files, no dependency):
Task: "Contract check sales: POST without number returns 201 (run backend/apps/sales/tests/test_auto_invoice_number.py)"
Task: "Contract check purchase: POST without number returns 201 (run backend/apps/purchases/tests/test_auto_invoice_number.py)"
Task: "Add disabled Number preview, omit number from payload in frontend/src/components/sales/invoices/InvoiceForm.jsx"
Task: "Add disabled Number preview, omit number from payload in frontend/src/components/purchases/invoices/PurchaseInvoiceForm.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T010, CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (T011-T017)
4. **STOP and VALIDATE**: Open each create dialog → disabled preview → save valid invoice → list shows number → reopen shows next
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 sales side (T011, T013, T015)
   - Developer B: User Story 1 purchase side (T012, T014, T016)
   - Developer C: User Story 2 (T018-T019) then User Story 3 (T020-T021)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group (via hook; no push/deploy)
- Stop at any checkpoint to validate story independently
- Unlike 015 (new service class), Foundational here extends two existing services with per-type helpers; duplicate-reject behavior is preserved, never idempotent
