# Tasks: Auto Vendor Code

**Input**: Design documents from `/specs/015-auto-vendor-code/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: New backend mint tests are written first as the verification gate (`test_auto_vendor_code.py`, mirroring `test_auto_customer_code.py`); existing `test_vendors_api.py` runs unchanged as a regression gate. T012 extends coverage only if the concurrent-preview path is uncovered.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/apps/purchases/`, `frontend/src/`
- Paths below are repo-relative per plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm toolchains run before any story work

- [X] T001 Verify backend test toolchain runs in backend/ (`DJANGO_SETTINGS_MODULE=config.settings.test`)
- [X] T002 [P] Verify frontend toolchain builds in frontend/ (`npm run build`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Authoritative backend mint path for vendors — MUST complete before ANY user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Write failing mint tests first in backend/apps/purchases/tests/test_auto_vendor_code.py (sequence VEN-0001/VEN-0002, blank-mint, edit-preserves-code, cross-tenant independence)
- [X] T004 [P] Implement VendorService with tenant-scoped next-code helper (VEN- prefix, collision-skip) and create_with_flag in backend/apps/purchases/services.py
- [X] T005 [P] Accept blank/missing code on create (no code-required rejection) in backend/apps/purchases/serializers.py
- [X] T006 Thin create view to delegate to VendorService, returning 201 with minted code and 200 on idempotent explicit-code duplicate in backend/apps/purchases/views.py (depends on T004, T005)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create a vendor with an auto-generated code (Priority: P1) 🎯 MVP

**Goal**: Create dialog shows a disabled Code preview (`VEN-0001`, +1 per saved vendor); saving without typing a code succeeds with the shown (or next free) code and no "code required" error

**Independent Test**: Open create dialog (code visible, not editable) → save with only a name → saved vendor carries the shown code; reopen shows the next code

### Implementation for User Story 1

- [X] T007 [P] [US1] Contract check: POST without code returns 201 with minted code per specs/015-auto-vendor-code/contracts/vendor-create.md (run backend/apps/purchases/tests/test_auto_vendor_code.py)
- [X] T008 [P] [US1] Add disabled Code preview in create mode, keep code out of create/update payloads, and return saved vendor via onSaved in frontend/src/components/purchases/vendors/VendorModal.jsx
- [X] T009 [US1] Add next-code preview helper, wire preview into modal, and surface assigned-code note when save returns a different code in frontend/src/pages/purchases/VendorsPage.jsx (depends on T008)
- [X] T010 [US1] Manual browser walkthrough per specs/015-auto-vendor-code/quickstart.md (preview → save → list → reopen shows next)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Codes increment by 1 per saved vendor (Priority: P2)

**Goal**: Every saved vendor gets the next sequential code (+1 from the highest existing code); collisions are skipped, sequences are per-business independent, gaps never reused

**Independent Test**: Create several vendors in a row → codes run VEN-0001, VEN-0002, … with +1 each; two viewers of the same preview both save successfully with different codes

### Implementation for User Story 2

- [X] T011 [P] [US2] Verify collision-skip and per-business independence tests in backend/apps/purchases/tests/test_auto_vendor_code.py
- [X] T012 [US2] Cover concurrent-preview scenario (second save gets next free code plus note), extending backend/apps/purchases/tests/test_auto_vendor_code.py only if uncovered

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Code is preserved and read-only on edit (Priority: P3)

**Goal**: Edit dialog shows code read-only; edits never blank, regenerate, or change it

**Independent Test**: Edit a vendor's name → code unchanged and still present

### Implementation for User Story 3

- [X] T013 [US3] Verify edit dialog shows code read-only and save preserves it in frontend/src/components/purchases/vendors/VendorModal.jsx
- [X] T014 [P] [US3] Verify edit-preserves-code test in backend/apps/purchases/tests/test_auto_vendor_code.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full verification with no regressions

- [X] T015 Run full backend suite green in backend/ (`py -m pytest apps/ -q`, expect no regressions vs 375 passed / 1 skipped baseline)
- [X] T016 [P] Run frontend build plus lint with zero new problems in frontend/
- [X] T017 Confirm migration check clean in backend/ (`py manage.py makemigrations --check --dry-run`, expect "No changes detected")

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
- T003 (new test file) can be written alongside T004/T005 exploration (different files)
- T007 + T008 (backend contract check vs frontend modal edit, different files)
- T011 + T014 (different verification targets, no shared files)
- T015 + T016 (backend suite vs frontend build/lint, independent)
- After Foundational, US1/US2/US3 can proceed in parallel if staffed

---

## Parallel Example: User Story 1

```bash
# Launch contract check and modal edit together (different files, no dependency):
Task: "Contract check: POST without code returns 201 with minted code (run backend/apps/purchases/tests/test_auto_vendor_code.py)"
Task: "Add disabled Code preview in create mode, keep code out of payloads, return saved vendor in frontend/src/components/purchases/vendors/VendorModal.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T006, CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (T007-T010)
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
   - Developer A: User Story 1 (T007-T010)
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
- Unlike 014 (backend already landed), Foundational here is real implementation: new VendorService + serializer + view thinning, with tests written first (T003)
