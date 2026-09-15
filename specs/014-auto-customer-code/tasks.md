# Tasks: Auto Customer Code

**Input**: Design documents from `/specs/014-auto-customer-code/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Existing backend mint tests are reused as verification gates (`test_auto_customer_code.py`, `test_customer_api_create_without_code.py`); T012 extends coverage only if the concurrent-preview path is uncovered.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/apps/sales/`, `frontend/src/`
- Paths below are repo-relative per plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm toolchains run before any story work

- [ ] T001 Verify backend test toolchain runs in backend/ (`DJANGO_SETTINGS_MODULE=config.settings.test`)
- [ ] T002 [P] Verify frontend toolchain builds in frontend/ (`npm run build`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Authoritative backend mint path confirmed green — MUST complete before ANY user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Confirm tenant-scoped next-code helper with collision-skip in backend/apps/sales/services.py
- [ ] T004 Confirm serializer accepts blank code on create (no code-required rejection) in backend/apps/sales/serializers.py
- [ ] T005 Confirm create view returns 201 with minted code and 200 on idempotent explicit-code duplicate in backend/apps/sales/views.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create a customer with an auto-generated code (Priority: P1) 🎯 MVP

**Goal**: Create dialog shows a disabled Code preview (`CUS-0001`, +1 per saved customer); saving without typing a code succeeds with the shown (or next free) code and no "code required" error

**Independent Test**: Open create dialog (code visible, not editable) → save with only a name → saved customer carries the shown code; reopen shows the next code

### Implementation for User Story 1

- [ ] T006 [P] [US1] Contract check: POST without code returns 201 with minted code per specs/014-auto-customer-code/contracts/customer-create.md (run backend/apps/sales/tests/test_customer_api_create_without_code.py)
- [ ] T007 [P] [US1] Add disabled Code preview showing the next code in create mode in frontend/src/components/sales/customers/CustomerModal.jsx
- [ ] T008 [US1] Keep code out of create and update payloads in frontend/src/components/sales/customers/CustomerModal.jsx (depends on T007)
- [ ] T009 [US1] Surface assigned-code note when save returns a code different from the preview in frontend/src/components/sales/customers/CustomerModal.jsx (depends on T007)
- [ ] T010 [US1] Manual browser walkthrough per specs/014-auto-customer-code/quickstart.md (preview → save → list → reopen shows next)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Codes increment by 1 per saved customer (Priority: P2)

**Goal**: Every saved customer gets the next sequential code (+1 from the highest existing code); collisions are skipped, sequences are per-business independent, gaps never reused

**Independent Test**: Create several customers in a row → codes run CUS-0001, CUS-0002, … with +1 each; two viewers of the same preview both save successfully with different codes

### Implementation for User Story 2

- [ ] T011 [P] [US2] Verify collision-skip and per-business independence tests in backend/apps/sales/tests/test_auto_customer_code.py
- [ ] T012 [US2] Cover concurrent-preview scenario (second save gets next free code plus note), extending backend/apps/sales/tests/test_auto_customer_code.py only if uncovered

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Code is preserved and read-only on edit (Priority: P3)

**Goal**: Edit dialog shows code read-only; edits never blank, regenerate, or change it

**Independent Test**: Edit a customer's name → code unchanged and still present

### Implementation for User Story 3

- [ ] T013 [US3] Verify edit dialog shows code read-only and save preserves it in frontend/src/components/sales/customers/CustomerModal.jsx
- [ ] T014 [P] [US3] Verify edit-preserves-code test in backend/apps/sales/tests/test_auto_customer_code.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full verification with no regressions

- [ ] T015 Run full backend suite green in backend/ (`py -m pytest apps/ -q`, expect no regressions vs baseline)
- [ ] T016 [P] Run frontend build plus lint with zero new problems in frontend/
- [ ] T017 Confirm migration check clean in backend/ (`py manage.py makemigrations --check --dry-run`, expect "No changes detected")

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
- Core implementation before integration (note-surfacing after preview)
- Story complete before moving to next priority

### Parallel Opportunities

- T001 + T002 (separate toolchains, no shared files)
- T006 + T007 (backend contract check vs frontend preview edit, different files)
- T011 + T014 (different verification targets, no shared files)
- T015 + T016 (backend suite vs frontend build/lint, independent)
- After Foundational, US1/US2/US3 can proceed in parallel if staffed

---

## Parallel Example: User Story 1

```bash
# Launch contract check and preview edit together (different files, no dependency):
Task: "Contract check: POST without code returns 201 with minted code (run backend/apps/sales/tests/test_customer_api_create_without_code.py)"
Task: "Add disabled Code preview showing the next code in create mode in frontend/src/components/sales/customers/CustomerModal.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005, CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (T006-T010)
4. **STOP and VALIDATE**: Open create dialog → disabled preview → save with name only → list shows code → reopen shows next
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
   - Developer A: User Story 1 (T006-T010)
   - Developer B: User Story 2 (T011-T012)
   - Developer C: User Story 3 (T013-T014)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group (via hook; no push/deploy)
- Stop at any checkpoint to validate story independently
- Backend mint path already landed and green — Foundational tasks are confirm-gates, not rewrites
