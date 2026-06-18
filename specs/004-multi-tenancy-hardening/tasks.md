---

description: "Task list for Multi-Tenancy Hardening implementation"

---

# Tasks: Multi-Tenancy Hardening

**Input**: Design documents from `specs/004-multi-tenancy-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are not requested — this feature hardens existing functionality without new endpoints. Existing 36 tests serve as the regression safety net.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` at repository root
- **Frontend**: Not affected by this feature

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Schema-level hardening that all user stories depend on.

- [ ] T001 Add `TenantScopedQuerySet` with `for_tenant()` method to `backend/apps/core/models.py`
- [ ] T002 Change `TenantScopedModel.tenant` from `null=True` to `null=False` in `backend/apps/core/models.py`
- [ ] T003 Add `db_index=True` to `Membership.tenant` field in `backend/apps/accounts/models.py`

**Checkpoint**: Shared infrastructure ready — abstract base enforces non-null tenant, query scoping method exists, membership index is configured.

---

## Phase 2: User Story 1 - Active middleware enforcement (Priority: P1) 🎯 MVP

**Goal**: An authenticated user cannot access a tenant they don't belong to. The middleware proactively rejects cross-tenant access with 403 before any business logic runs.

**Independent Test**: An authenticated user sends a request with a tenant ID they have no membership for and receives 403 Forbidden. An authenticated user with valid membership proceeds normally. Unauthenticated public endpoints are unaffected.

### Implementation for User Story 1

- [ ] T004 [US1] Rewrite `TenantResolutionMiddleware` in `backend/apps/core/middleware.py` — parse JWT from Authorization header, extract tenant_id claim, fall back to X-TENANT-ID header, validate UUID format, query Membership for active validation, set `request.tenant_id` as UUID
- [ ] T005 [P] [US1] Update `InvitationService.list_pending` in `backend/apps/accounts/services.py` to use `Invitation.objects.for_tenant(tenant_id)` instead of `.filter(tenant_id=tenant_id)`
- [ ] T006 [P] [US1] Update `InvitationService.create_invitation` in `backend/apps/accounts/services.py` to use `.for_tenant()` for the duplicate check
- [ ] T007 [P] [US1] Update `InvitationService.cancel_invitation` in `backend/apps/accounts/services.py` to use `.for_tenant()` for the delete query
- [ ] T008 [P] [US1] Update `TeamService.list_members` in `backend/apps/accounts/services.py` to use `Membership.objects.for_tenant(tenant_id)`
- [ ] T009 [P] [US1] Update `TeamService.change_role` admin count query in `backend/apps/accounts/services.py` to use `.for_tenant()`
- [ ] T010 [P] [US1] Update `TeamService.remove_member` admin count query in `backend/apps/accounts/services.py` to use `.for_tenant()`

**Checkpoint**: US1 complete — middleware rejects cross-tenant access, all service queries use explicit `for_tenant()` scoping.

---

## Phase 3: User Story 2 - Membership query performance (Priority: P2)

**Goal**: Tenant-filtered membership queries are fast regardless of total system size, thanks to the new index on `Membership.tenant_id`.

**Independent Test**: EXPLAIN ANALYZE on a `SELECT * FROM accounts_membership WHERE tenant_id = '<uuid>'` shows an Index Scan, not a Seq Scan. The schema change is already in T003 — this phase verifies it works.

### Implementation for User Story 2

- [ ] T011 [US2] Generate and apply the `db_index` migration for `Membership.tenant` in `backend/apps/accounts/migrations/`

**Checkpoint**: US2 complete — the index exists on `accounts_membership.tenant_id` and is verified in the migration.

---

## Phase 4: User Story 3 - Tenant-scoped NOT NULL enforcement (Priority: P3)

**Goal**: No tenant-scoped record can be created without a tenant FK. The `TenantScopedModel` abstract base enforces this at the schema level.

**Independent Test**: An attempt to INSERT an Invitation with `tenant_id = NULL` is rejected by the database with a NOT NULL constraint violation. The schema change is already in T002 — this phase verifies it works.

### Implementation for User Story 3

- [ ] T012 [US3] Generate and apply the NOT NULL migration for `Invitation.tenant_id` in `backend/apps/accounts/migrations/` (run data cleanup first — delete or assign any existing invitations with null tenant)

**Checkpoint**: US3 complete — the NOT NULL constraint exists on `accounts_invitation.tenant_id`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [ ] T013 [P] Run existing test suite to verify 36 tests still pass
- [ ] T014 [P] Run quickstart validation scenarios from `specs/004-multi-tenancy-hardening/quickstart.md`
- [ ] T015 Update `AGENTS.md` with quick reference for this feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — foundational infrastructure for all stories
- **User Story 1 (Phase 2)**: Depends on Setup completion (T001 for `for_tenant()`, T002 for NOT NULL)
- **User Story 2 (Phase 3)**: Depends on Setup completion only (T003 configures the index)
- **User Story 3 (Phase 4)**: Depends on Setup completion only (T002 configures NOT NULL; T012 generates the migration)
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Setup (T001) — uses `for_tenant()` method
- **User Story 2 (P2)**: Depends on Setup (T003 configures the field; T011 generates migration)
- **User Story 3 (P3)**: Depends on Setup (T002 configures the field; T012 generates migration)
- US2 and US3 can run in parallel with each other and with US1 — they touch different files

### Within Each User Story

- Models/config before migrations
- Services before middleware
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (different files)
- All US1 service tasks (T005–T010) can run in parallel (different methods in services.py)
- US2 (T011) and US3 (T012) can run in parallel with US1 or each other — independent migrations
- Polish tasks [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 service updates together:
Task: T005 Update InvitationService.list_pending
Task: T006 Update InvitationService.create_invitation
Task: T007 Update InvitationService.cancel_invitation
Task: T008 Update TeamService.list_members
Task: T009 Update TeamService.change_role
Task: T010 Update TeamService.remove_member

# Middleware is sequential (after services):
Task: T004 Rewrite TenantResolutionMiddleware
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: User Story 1 (T004–T010)
3. **STOP and VALIDATE**: Test US1 independently — run test suite, manual cross-tenant rejection test
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup → multi-tenancy infrastructure hardened
2. Add US1 → Active middleware enforcement → Deploy/Demo (MVP!)
3. Add US2 → Query performance → Deploy/Demo
4. Add US3 → Schema integrity → Deploy/Demo

### Parallel Team Strategy

With multiple developers:

1. Setup (Phase 1): Together — model changes in core/models.py + accounts/models.py
2. Once Setup is done:
   - Developer A: US1 middleware + service updates (T004–T010)
   - Developer B: US2 + US3 migrations (T011, T012)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Services use `for_tenant()` instead of direct `.filter(tenant_id=...)` — makes scoping visible
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
