---
description: "Task list for Docker Compose Infrastructure feature implementation"

---

# Tasks: Docker Compose Infrastructure

**Input**: Design documents from `specs/003-docker-compose-infrastructure/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are NOT requested for this infrastructure feature — validation is done via manual quickstart scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Infra**: `infra/` at repository root (docker-compose.yml, Dockerfile)
- **Backend**: `backend/` at repository root
- **Frontend**: `frontend/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Redis and Celery dependencies to the backend so all services can use them.

- [ ] T001 [P] Add `redis` and `celery` to `backend/requirements/base.txt`
- [ ] T002 [P] Create Celery app config in `backend/config/celery.py`
- [ ] T003 Create Django Celery settings in `backend/config/settings/dev.py` (broker URL, result backend)
- [ ] T004 Create Redis cache config in `backend/config/settings/dev.py` (CACHES setting using Redis)
- [ ] T005 [P] Create helper module for Redis connectivity check at `backend/apps/core/health.py`

**Checkpoint**: Dependencies and config ready — backend can import Celery and connect to Redis when available.

---

## Phase 2: User Story 1 - Developer starts full application stack (Priority: P1) 🎯 MVP

**Goal**: A developer runs `docker compose -f infra/docker-compose.yml up` and the backend, frontend, PostgreSQL, and Redis all start.

**Independent Test**: A new developer checks out the repo, runs the start command, and accesses both backend health at localhost:8000/api/v1/health/ and frontend at localhost:5173.

### Implementation for User Story 1

- [ ] T006 [P] [US1] Add Redis service to `infra/docker-compose.yml` (redis:7-alpine, health check, not exposed to host)
- [ ] T007 [P] [US1] Add `REDIS_HOST` and `REDIS_PORT` environment variables to the backend service in `infra/docker-compose.yml`
- [ ] T008 [US1] Update backend startup command in `infra/Dockerfile` to run migrations + gunicorn
- [ ] T009 [US1] Update `infra/Dockerfile` to install `redis` and `celery` pip dependencies from requirements
- [ ] T010 [P] [US1] Create or update health check endpoint at `backend/apps/core/views.py` that checks DB + Redis connectivity
- [ ] T011 [US1] Wire health check URL in `backend/config/urls.py`
- [ ] T012 [US1] Update frontend `vite.config.js` to proxy `/api/` requests to backend if not already configured

**Checkpoint**: At this point, `docker compose up` starts all 4 services and the health endpoint reports green.

---

## Phase 3: User Story 2 - Developer accesses a database with initialized schema (Priority: P2)

**Goal**: The PostgreSQL service persists data across restarts and initializes with UUID extension.

**Independent Test**: A developer stops the stack, restarts, and previously created data is still accessible.

### Implementation for User Story 2

- [ ] T013 [US2] Verify and update `infra/docker-compose.yml` db service has a named volume (`pgdata`) for persistence
- [ ] T014 [US2] Verify `infra/init-db.sql` enables `uuid-ossp` extension on database initialization
- [ ] T015 [US2] Add `depends_on` with `condition: service_healthy` for the db service to ensure startup ordering in `infra/docker-compose.yml`

**Checkpoint**: Database persists data across restarts and initializes with required extensions.

---

## Phase 4: User Story 3 - Redis cache is available for the backend (Priority: P3)

**Goal**: The backend connects to Redis for caching, improving API response times.

**Independent Test**: A developer verifies the backend connects to Redis and cached queries return faster than uncached ones.

### Implementation for User Story 3

- [ ] T016 [US3] Add Redis health check probe to `infra/docker-compose.yml` redis service
- [ ] T017 [US3] Add `depends_on` redis with health check condition to the backend service in `infra/docker-compose.yml`
- [ ] T018 [US3] Wire the Redis cache backend into Django's `CACHES` setting in `backend/config/settings/dev.py`
- [ ] T019 [P] [US3] Add Redis connection verification to the health check endpoint at `backend/apps/core/health.py`

**Checkpoint**: Backend uses Redis as cache backend; health check reports Redis connectivity.

---

## Phase 5: User Story 4 - Background worker processes tasks asynchronously (Priority: P4)

**Goal**: An opt-in Celery worker service processes background tasks (auto-categorization, reconciliation, insights).

**Independent Test**: A developer starts the stack with `--profile worker`, submits a background task, and observes the worker processing it.

### Implementation for User Story 4

- [ ] T020 [US4] Create Celery app singleton in `backend/config/celery.py` (auto-discover tasks from registered apps)
- [ ] T021 [US4] Add Celery config to `backend/config/settings/dev.py` (broker_url, result_backend pointing to Redis)
- [ ] T022 [P] [US4] Add worker service to `infra/docker-compose.yml` under `profiles: ["worker"]` with Celery command
- [ ] T023 [US4] Add `CELERY_BROKER_URL` environment variable to the worker service in `infra/docker-compose.yml`
- [ ] T024 [US4] Create placeholder task module at `backend/apps/accounts/tasks.py` for future auto-categorization tasks

**Checkpoint**: Worker can be started with `--profile worker` and connects to Redis broker + database.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [ ] T025 [P] Update `AGENTS.md` with Docker Compose quick reference commands
- [ ] T026 Run quickstart validation scenarios from `specs/003-docker-compose-infrastructure/quickstart.md` — all 6 scenarios must pass
- [ ] T027 Code cleanup: remove any unused `local.py` or test DB files from the active branch

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — foundational dependency configuration
- **User Story 1 (Phase 2)**: Depends on Setup completion (T001-T005)
- **User Story 2 (Phase 3)**: Depends on Phase 2 (uses the stack to validate) — minimal changes, mostly verification
- **User Story 3 (Phase 4)**: Depends on Setup + US1 (Redis must be in compose, health endpoint must exist)
- **User Story 4 (Phase 5)**: Depends on Setup + US3 (Celery needs Redis as broker)
- **Polish (Phase 6)**: Depends on all selected user stories being complete

### Within Each User Story

- Docker compose changes before Dockerfile changes
- Config before endpoints
- Service added to compose before backend code changes
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T001 requirements, T002 celery app, T005 health helper)
- T006 (Redis service) and T007 (env vars) within US1 can run in parallel
- T022 (worker service) and T023 (worker env vars) within US4 can run in parallel
- US3 (Redis as cache) and US4 (worker) share Redis dependency but touch different files

---

## Parallel Example: User Story 1

```bash
# Launch all composable changes for US1 together:
Task: T006 [P] [US1] Add Redis service to infra/docker-compose.yml
Task: T007 [P] [US1] Add REDIS_HOST and REDIS_PORT env vars to backend service
Task: T010 [P] [US1] Create or update health check endpoint

# Then wire them together:
Task: T008 [US1] Update backend startup command in Dockerfile
Task: T011 [US1] Wire health check URL
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3)

1. Complete Phase 1: Setup (requirements, Celery config, Django settings)
2. Complete Phase 2: User Story 1 (Redis in compose, health endpoint)
3. Complete Phase 3: User Story 2 (DB persistence — mostly verification)
4. Complete Phase 4: User Story 3 (Redis as cache backend + health check)
5. **STOP and VALIDATE**: Test full stack with Redis caching
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup → Redis + Celery dependencies ready
2. Add US1 → Full stack runs with one command → Deploy/Demo
3. Add US2 → Database persists across restarts → Deploy/Demo
4. Add US3 → Redis caching improves performance → Deploy/Demo
5. Add US4 → Worker available for background tasks (opt-in)

### Parallel Team Strategy

With multiple developers:

1. Setup (Phase 1): Together — requirements, Celery app, Django settings
2. Once Setup is done:
   - Developer A: US1 + US3 (compose changes + cache wiring)
   - Developer B: US2 + US4 (DB persistence verification + worker profile)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- US4 (worker) is explicitly P4 — can be deferred to a later iteration without blocking other stories
