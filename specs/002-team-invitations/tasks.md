---
description: "Task list for Team Invitations feature implementation"

---

# Tasks: Team Invitations

**Input**: Design documents from `specs/002-team-invitations/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included. Write them BEFORE implementation (fail first, then implement).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` at repository root
- **Frontend**: `frontend/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Model, services, and permission logic shared across all team management stories.

- [X] T001 Create Invitation model in `backend/apps/accounts/models.py` (inherits TenantScopedModel, fields: email, role, token unique, expires_at, accepted_at nullable)
- [X] T002 [P] Create team permission check (`IsAdminUser`) in `backend/apps/accounts/permissions.py`
- [X] T003 [P] Create InvitationService in `backend/apps/accounts/services.py` (create_invitation, validate_token, accept_invitation, cancel_invitation)
- [X] T004 [P] Create TeamService in `backend/apps/accounts/services.py` (list_members, change_role, remove_member, is_last_admin)
- [X] T005 [P] Create team serializers in `backend/apps/accounts/serializers.py` (InvitationSerializer, InvitationCreateSerializer, MemberSerializer, RoleChangeSerializer)
- [X] T006 Create and apply database migration for Invitation model in `backend/apps/accounts/migrations/`

**Checkpoint**: Shared infrastructure ready — invitations can be created, validated, accepted, and cancelled; member operations are stubbed.

---

## Phase 2: User Story 1 - Admin invites a new member via email (Priority: P1) 🎯 MVP

**Goal**: An admin can invite a person by email, and that person can register with the invitation token to join the tenant.

**Independent Test**: An admin creates an invitation for a new email, and that person registers with the token, sees the company in their tenant list, and accesses it with the correct role.

### Tests for User Story 1 ⚠️

- [X] T007 [P] [US1] Test create invitation returns 201 for admin in `backend/apps/accounts/tests/test_team_api.py`
- [X] T008 [P] [US1] Test create invitation returns 403 for non-admin in `backend/apps/accounts/tests/test_team_api.py`
- [X] T009 [P] [US1] Test create duplicate pending invitation returns 400 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T010 [P] [US1] Test register with valid invitation token returns 201 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T011 [P] [US1] Test register with expired invitation token returns 400 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T012 [P] [US1] Test register with invalid invitation token returns 400 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T013 [P] [US1] Test register with already-accepted invitation token returns 400 in `backend/apps/accounts/tests/test_team_api.py`

### Implementation for User Story 1

- [X] T014 [US1] Create invitation create and list views in `backend/apps/accounts/views.py` (invitation_list_create_view)
- [X] T015 [US1] Add invitation endpoints to `backend/apps/accounts/urls.py` (POST + GET `/api/v1/tenants/invitations/`)
- [X] T016 [US1] Modify register_view in `backend/apps/accounts/views.py` to accept optional `invitation_token` parameter
- [X] T017 [US1] Update RegisterSerializer in `backend/apps/accounts/serializers.py` to include invitation_token field
- [X] T018 [US1] Update frontend RegisterPage in `frontend/src/pages/RegisterPage.jsx` to read `?token=` from URL and pass it to the register API

**Checkpoint**: US1 complete — admin invites, new user registers with token, auto-joins tenant.

---

## Phase 3: User Story 2 - Existing user invited to a new tenant (Priority: P1)

**Goal**: A user who already has an account is invited to a different tenant. They don't re-register — the tenant appears in their list on next login.

**Independent Test**: An existing user who is invited to a new tenant logs in and sees the new tenant in their tenant selection screen.

### Tests for User Story 2 ⚠️

- [X] T019 [P] [US2] Test existing user invited sees new tenant on login in `backend/apps/accounts/tests/test_team_api.py`
- [X] T020 [P] [US2] Test login response includes all memberships (tenants) in `backend/apps/accounts/tests/test_team_api.py`

### Implementation for User Story 2

- [X] T021 [US2] Update InvitationService.accept_invitation to create Membership for existing users (no registration)
- [X] T022 [US2] Implement tenant switch endpoint in `backend/apps/accounts/views.py` (tenant_switch_view)
- [X] T023 [US2] Add tenant switch URL to `backend/apps/accounts/urls.py` (POST `/api/v1/tenants/switch/{tenant_id}/`)
- [X] T024 [US2] Create TenantSwitcher React component in `frontend/src/components/Layout/TenantSwitcher.jsx` (dropdown to switch active tenant, display current tenant name)

**Checkpoint**: US2 complete — existing user gets new tenant in list, can switch via dropdown.

---

## Phase 4: User Story 3 - Admin manages team members and roles (Priority: P2)

**Goal**: Admin can view all members, change roles, and remove members. Last admin cannot be removed or demoted.

**Independent Test**: An admin navigates to team management, sees all members with their roles, changes a member's role, and removes a non-admin member.

### Tests for User Story 3 ⚠️

- [X] T025 [P] [US3] Test list members returns 200 with member list in `backend/apps/accounts/tests/test_team_api.py`
- [X] T026 [P] [US3] Test list members returns 403 for non-admin in `backend/apps/accounts/tests/test_team_api.py`
- [X] T027 [P] [US3] Test change member role returns 200 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T028 [P] [US3] Test change last admin role returns 400 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T029 [P] [US3] Test remove member returns 204 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T030 [P] [US3] Test remove last admin returns 400 in `backend/apps/accounts/tests/test_team_api.py`

### Implementation for User Story 3

- [X] T031 [US3] Create member list, role change, and remove views in `backend/apps/accounts/views.py` (member_list_view, member_role_update_view, member_destroy_view)
- [X] T032 [US3] Add member endpoints to `backend/apps/accounts/urls.py` (GET members, PATCH members/{id}/role, DELETE members/{id})
- [X] T033 [P] [US3] Create TeamPage React component in `frontend/src/pages/TeamPage.jsx` (member list table, invite form, role change dropdown, remove button)
- [X] T034 [US3] Wire up TeamPage route in `frontend/src/App.jsx`

**Checkpoint**: US3 complete — admin manages team with last-admin protection.

---

## Phase 5: User Story 4 - Admin cancels a pending invitation (Priority: P3)

**Goal**: Admin can view all pending invitations and cancel any that are no longer needed.

**Independent Test**: Admin sees a list of pending invitations and cancels one, preventing its use for registration.

### Tests for User Story 4 ⚠️

- [X] T035 [P] [US4] Test list pending invitations returns 200 for admin in `backend/apps/accounts/tests/test_team_api.py`
- [X] T036 [P] [US4] Test cancel invitation returns 204 in `backend/apps/accounts/tests/test_team_api.py`
- [X] T037 [P] [US4] Test register with cancelled token returns 400 in `backend/apps/accounts/tests/test_team_api.py`

### Implementation for User Story 4

- [X] T038 [US4] Create invitation destroy view (`invitation_destroy_view`) in `backend/apps/accounts/views.py`
- [X] T039 [US4] Add DELETE invitation endpoint to `backend/apps/accounts/urls.py` (DELETE `/api/v1/tenants/invitations/{id}/`)
- [X] T040 [P] [US4] Add pending invitations section to TeamPage in `frontend/src/pages/TeamPage.jsx` (list of pending invites with cancel button)

**Checkpoint**: US4 complete — admin can cancel pending invitations.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [X] T041 [P] Add email display in login response for tenant switch flow verification — updated TenantSwitcher.jsx to show userEmail from localStorage
- [X] T042 [P] Add unit tests for edge cases (cross-tenant duplicate email succeeds, invite existing member succeeds, tenant isolation for invites/members)
- [X] T043 Run quickstart validation scenarios from `specs/002-team-invitations/quickstart.md` — all 8 scenarios verified by tests (36/36 passing)
- [X] T044 Code cleanup and documentation updates in `AGENTS.md`
- [X] T045 [P] Security hardening pass: all 6 team endpoints use `[IsAuthenticated, IsAdminUser]`, service layer scopes by tenant_id, token uses `secrets.token_urlsafe(48)`, `IsAdminUser` validates user is ADMIN in the tenant, `cancel_invitation` checks both id and tenant_id

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — foundational infrastructure for all stories
- **User Story 1 (Phase 2)**: Depends on Setup completion (InvitationService, model, migration)
- **User Story 2 (Phase 3)**: Depends on Setup completion + US1 (uses InvitationService.accept_invitation)
- **User Story 3 (Phase 4)**: Depends on Setup completion (TeamService) — independently testable
- **User Story 4 (Phase 5)**: Depends on Setup completion (InvitationService) — can run in parallel with US3
- **Polish (Phase 6)**: Depends on all selected user stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Services before endpoints
- Endpoints before frontend integration
- Story complete before moving to next priority

### Parallel Opportunities

- All US1 tests marked [P] can run in parallel
- All US3 tests marked [P] can run in parallel
- US3 (backend) and US4 (backend) can be implemented in parallel since they use different services
- Frontend pages for different stories can be built in parallel once endpoints exist
- US1 frontend (RegisterPage modification) and US4 frontend (TeamPage invite section) touch different parts of the UI

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: T007 [P] [US1] Test create invitation success
Task: T008 [P] [US1] Test create invitation as non-admin
Task: T009 [P] [US1] Test duplicate invitation
Task: T010 [P] [US1] Test register with valid token
Task: T011 [P] [US1] Test register with expired token
Task: T012 [P] [US1] Test register with invalid token
Task: T013 [P] [US1] Test register with accepted token

# Launch invitation view + URL together:
Task: T014 [US1] Create invitation views
Task: T015 [US1] Add invitation URLs
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (Invitation model, services, migration)
2. Complete Phase 2: User Story 1 (admin invites new user)
3. Complete Phase 3: User Story 2 (existing user invited)
4. **STOP and VALIDATE**: Test US1 + US2 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup → Team invitations infrastructure ready
2. Add US1 → Admin can invite new users → Deploy/Demo
3. Add US2 → Existing users join new tenants → Deploy/Demo
4. Add US3 → Admin manages team (roles, removal) → Deploy/Demo
5. Add US4 → Admin cancels invitations → Deploy/Demo

### Parallel Team Strategy

With multiple developers:

1. Setup (Phase 1): Together — model, services, migration
2. Once Setup is done:
   - Developer A: US1 + US2 (invitation flow + registration)
   - Developer B: US3 + US4 (member management + cancellation)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
