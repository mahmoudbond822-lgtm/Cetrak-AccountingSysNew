---

description: "Task list for Project Foundation feature implementation"

---

# Tasks: Project Foundation

**Input**: Design documents from `specs/001-project-foundation/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Test tasks are included. Write them BEFORE implementation (fail first, then implement).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/` at repository root
- **Frontend**: `frontend/` at repository root
- **Infra**: `infra/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create `backend/` directory structure with Django project skeleton in `backend/config/`
- [X] T002 Create Django apps directory `backend/apps/` with placeholder apps: core, accounts, accounting, sales, purchases
- [X] T003 Create `backend/requirements/base.txt`, `dev.txt`, `prod.txt` with Django, DRF, psycopg2-binary, simplejwt, pytest, pytest-django
- [X] T004 Create `backend/pytest.ini` with Django test configuration
- [X] T005 Create `frontend/` directory with React project skeleton using Create React App or Vite
- [X] T006 Create `infra/docker-compose.yml` with PostgreSQL 15, backend, and frontend services
- [X] T007 [P] Create `infra/Dockerfile` for backend production build
- [X] T008 [P] Create `frontend/.env` with API base URL configuration

**Checkpoint**: Project skeleton ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 Create `backend/config/settings/base.py` with Django settings (database, installed apps, middleware, JWT config, REST framework config)
- [X] T010 [P] Create `backend/config/settings/dev.py` inheriting base with debug mode and SQL logging
- [X] T011 [P] Create `backend/config/settings/prod.py` inheriting base with production settings
- [X] T012 Create `backend/config/urls.py` with root URL routing and API v1 prefix
- [X] T013 [P] Create `backend/apps/core/models.py` with abstract BaseModel (UUID id, created_at, updated_at) and abstract TenantScopedModel (extends BaseModel, adds nullable tenant FK → Tenant)
- [X] T014 Create `backend/apps/core/models.py` with Tenant model (inherits BaseModel, fields: name, status: Active/Suspended/Cancelled)
- [X] T015 Create `backend/apps/core/middleware.py` with TenantResolutionMiddleware (extracts X-Tenant-ID header, injects into request, validates tenant exists and is Active, provides tenant-scoped queryset filtering for TenantScopedModel models)
- [X] T016 Create database migrations for core app and apply them
- [X] T017 [P] Configure PostgreSQL in Docker Compose with UUID extension enabled
- [ ] T018 Create database indexes for performance: tenant_id on all TenantScopedModel subclasses, unique (user_id, tenant_id) on Membership, email on User, token on Invitation

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Business owner signs up and logs in (Priority: P1) 🎯 MVP

**Goal**: A new business owner can register their company, create their admin account, and log into the system. Returning users can log in with email and password. Users with multiple tenants select one after login.

**Independent Test**: A new user can visit the signup page, complete registration with a company name, email, and password, then immediately log in and see an empty dashboard with their company name displayed.

### Tests for User Story 1 ⚠️

- [X] T019 [P] [US1] Test register success returns 201 with tokens in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T020 [P] [US1] Test register duplicate email returns 400 in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T021 [P] [US1] Test login success returns 200 with tokens in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T022 [P] [US1] Test login wrong password returns 401 in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T023 [P] [US1] Test login disabled user returns 403 in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T024 [P] [US1] Test login multi-tenant returns tenants array with null active_tenant in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T025 [P] [US1] Test token refresh returns new access token in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T026 [P] [US1] Test protected endpoint without token returns 401 in `backend/apps/accounts/tests/test_auth_api.py`
- [X] T027 [P] [US1] Test tenant isolation - user from tenant A cannot access tenant B data in `backend/apps/accounts/tests/test_tenant_isolation.py`

### Implementation for User Story 1

- [X] T028 [P] [US1] Create User model in `backend/apps/accounts/models.py` (inherits BaseModel, fields: email, password, display_name, status: Active/Invited/Disabled)
- [X] T029 [P] [US1] Create Membership model in `backend/apps/accounts/models.py` (inherits TenantScopedModel, user FK, tenant FK from base, role: Admin/Accountant/Manager, unique constraint on user+tenant)
- [X] T030 [US1] Configure Django REST Framework settings for JWT authentication in `backend/config/settings/base.py`
- [X] T031 [US1] Create AuthService in `backend/apps/accounts/services.py` (register: creates User + Tenant + Membership; login: validates credentials, checks user/tenant status, returns JWT tokens)
- [X] T032 [US1] Create auth serializers in `backend/apps/accounts/serializers.py` (RegisterSerializer, LoginSerializer, TokenRefreshSerializer)
- [X] T033 [US1] Create auth views in `backend/apps/accounts/views.py` (RegisterView, LoginView, LogoutView, TokenRefreshView)
- [X] T034 [US1] Create URL routing in `backend/apps/accounts/urls.py` with all auth endpoints under `/api/v1/auth/`
- [X] T035 [P] [US1] Create LoginPage React component in `frontend/src/pages/LoginPage.jsx` (email + password form, remember me checkbox, error display, redirect to dashboard or tenant select)
- [X] T036 [P] [US1] Create RegisterPage React component in `frontend/src/pages/RegisterPage.jsx` (email + company name + password form, auto-login on success)
- [X] T037 [P] [US1] Create DashboardPage React component in `frontend/src/pages/DashboardPage.jsx` (empty state with company name, logout button)
- [X] T038 [P] [US1] Create TenantSelectPage React component in `frontend/src/pages/TenantSelectPage.jsx` (list of tenants, pick one to proceed)
- [X] T039 [P] [US1] Create API service module in `frontend/src/services/api.js` (axios instance with base URL, token interceptor, tenant header, auth endpoints)
- [X] T040 [P] [US1] Create ProtectedRoute component in `frontend/src/components/Layout/ProtectedRoute.jsx` (redirects to login if not authenticated)
- [X] T041 [US1] Wire up App.jsx routing (React Router: login, register, dashboard, tenant-select pages) with protected routes

**Checkpoint**: User Story 1 complete — a user can register, log in, and see their dashboard with tenant isolation enforced.

---

## Phase 4: User Story 2 - Admin invites team members (Priority: P2)

**Goal**: An admin can invite team members by email, manage roles, and cancel invitations. Existing users can receive new tenant memberships without re-registering. Admins can view and manage team members.

**Independent Test**: An admin can navigate to team management, enter a new member's email address and assign a role, and that person can then register and access the same company's data with the assigned permissions.

### Tests for User Story 2 ⚠️

- [ ] T042 [P] [US2] Test create invitation returns 201 in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T043 [P] [US2] Test list invitations returns pending list in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T044 [P] [US2] Test cancel invitation returns 204 in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T045 [P] [US2] Test register with invitation token auto-joins tenant in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T046 [P] [US2] Test register with expired invitation token returns 400 in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T047 [P] [US2] Test existing user receives notification when invited to new tenant in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T048 [P] [US2] Test list members returns all members in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T049 [P] [US2] Test change member role returns 200 in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T050 [P] [US2] Test remove member returns 204 in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T051 [P] [US2] Test last admin cannot be removed or change role in `backend/apps/accounts/tests/test_team_api.py`
- [ ] T052 [P] [US2] Test non-admin cannot access team endpoints in `backend/apps/accounts/tests/test_team_api.py`

### Implementation for User Story 2

- [ ] T053 [P] [US2] Create Invitation model in `backend/apps/accounts/models.py` (inherits TenantScopedModel, tenant FK from base, email, role, token, expires_at, accepted_at)
- [ ] T054 [US2] Create InvitationService in `backend/apps/accounts/services.py` (create invitation, generate token, validate token, accept invitation, cancel invitation)
- [ ] T055 [US2] Create TeamService in `backend/apps/accounts/services.py` (list members, change role, remove member, last admin guard)
- [ ] T056 [US2] Create team serializers in `backend/apps/accounts/serializers.py` (InvitationSerializer, MemberSerializer, RoleChangeSerializer)
- [ ] T057 [US2] Create team views in `backend/apps/accounts/views.py` (InvitationListCreateView, InvitationDestroyView, MemberListView, MemberRoleUpdateView, MemberDestroyView)
- [ ] T058 [US2] Add team URLs to `backend/apps/accounts/urls.py` under `/api/v1/tenants/`
- [ ] T059 [US2] Update RegisterView to accept optional invitation_token parameter that auto-links to tenant
- [ ] T060 [P] [US2] Create TenantSwitcher component in `frontend/src/components/Layout/TenantSwitcher.jsx` (dropdown to switch active tenant, display current tenant name)
- [ ] T061 [P] [US2] Create team management page in `frontend/src/pages/TeamPage.jsx` (member list, invite form, role change dropdown, remove button)
- [ ] T062 [US2] Wire up team page routing and navigation in `frontend/src/App.jsx`

**Checkpoint**: User Stories 1 AND 2 should both work independently — admin can invite, users accept, team is managed.

---

## Phase 5: User Story 3 - User manages profile and resets password (Priority: P3)

**Goal**: Users can view and update their profile, change their password (requiring current password), and reset their password via email if forgotten.

**Independent Test**: A logged-in user can navigate to profile settings, change their display name and password, log out, and log back in with the new password.

### Tests for User Story 3 ⚠️

- [ ] T063 [P] [US3] Test get profile returns 200 with user data in `backend/apps/accounts/tests/test_profile_api.py`
- [ ] T064 [P] [US3] Test update profile returns 200 in `backend/apps/accounts/tests/test_profile_api.py`
- [ ] T065 [P] [US3] Test change password with correct current password returns 200 in `backend/apps/accounts/tests/test_profile_api.py`
- [ ] T066 [P] [US3] Test change password with wrong current password returns 400 in `backend/apps/accounts/tests/test_profile_api.py`
- [ ] T067 [P] [US3] Test request password reset returns 204 in `backend/apps/accounts/tests/test_profile_api.py`
- [ ] T068 [P] [US3] Test confirm password reset with valid token returns 200 in `backend/apps/accounts/tests/test_profile_api.py`
- [ ] T069 [P] [US3] Test confirm password reset with invalid token returns 400 in `backend/apps/accounts/tests/test_profile_api.py`

### Implementation for User Story 3

- [ ] T070 [US3] Create ProfileService in `backend/apps/accounts/services.py` (get profile, update profile, change password with current password validation)
- [ ] T071 [US3] Create PasswordResetService in `backend/apps/accounts/services.py` (request reset with email, confirm reset with token, integrate with Django's token generator)
- [ ] T072 [US3] Create profile serializers in `backend/apps/accounts/serializers.py` (ProfileSerializer, PasswordChangeSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer)
- [ ] T073 [US3] Create profile views in `backend/apps/accounts/views.py` (ProfileRetrieveUpdateView, PasswordChangeView, PasswordResetRequestView, PasswordResetConfirmView)
- [ ] T074 [US3] Add profile and password reset URLs to `backend/apps/accounts/urls.py`
- [ ] T075 [P] [US3] Create ProfilePage React component in `frontend/src/pages/ProfilePage.jsx` (display name edit, password change form)
- [ ] T076 [P] [US3] Wire up profile page routing in `frontend/src/App.jsx`

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T077 [P] Add email service integration for password reset and invitation emails in `backend/apps/accounts/services.py`
- [ ] T078 [P] Add rate limiting on login and password reset endpoints to prevent brute force
- [ ] T079 Add comprehensive error handling and consistent JSON error response format across all endpoints
- [ ] T080 [P] Add unit tests for edge cases (duplicate email registration, multi-tenant token switching, session expiry)
- [ ] T081 Run quickstart validation scenarios from `specs/001-project-foundation/quickstart.md` to verify end-to-end flows
- [ ] T082 Code cleanup and documentation updates in `AGENTS.md` and `docs/`
- [ ] T083 [P] Security hardening pass: verify bcrypt hashing, JWT expiry, tenant isolation in all views, CORS configuration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - No dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational completion - Integrates with US1 (users, auth) but independently testable
- **User Story 3 (Phase 5)**: Depends on Foundational completion - Integrates with US1 (users, auth) but independently testable
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Reuses User/Membership from US1 but can be tested independently with seeded data
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Reuses User model from US1 but tested independently

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel
- Once Foundational phase completes, all user stories can start in parallel
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Frontend and backend tasks within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: T019 [P] [US1] Test register success
Task: T020 [P] [US1] Test register duplicate email
Task: T021 [P] [US1] Test login success
Task: T022 [P] [US1] Test login wrong password
...

# Launch all models for User Story 1 together:
Task: T028 [P] [US1] Create User model
Task: T029 [P] [US1] Create Membership model

# Launch all frontend pages for User Story 1 together:
Task: T035 [P] [US1] Create LoginPage
Task: T036 [P] [US1] Create RegisterPage
Task: T037 [P] [US1] Create DashboardPage
Task: T038 [P] [US1] Create TenantSelectPage
Task: T039 [P] [US1] Create API service
Task: T040 [P] [US1] Create ProtectedRoute
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
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
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
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
