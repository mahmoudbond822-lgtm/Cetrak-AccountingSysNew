# Implementation Plan: Docker Compose Infrastructure

**Branch**: `003-docker-compose-infrastructure` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-docker-compose-infrastructure/spec.md`

## Summary

Add Redis and optional Celery worker services to the existing Docker Compose setup, ensuring the full development stack (backend, frontend, PostgreSQL, Redis) can be started with a single command. The existing `infra/docker-compose.yml` and `infra/Dockerfile` will be updated to add Redis, configure the backend to connect to it, and add an opt-in worker profile.

## Technical Context

**Language/Version**: Python 3.11+ (backend), Node.js 22 (frontend), Docker Compose V2

**Primary Dependencies**: Docker Engine 24+, Docker Compose V2, PostgreSQL 15 (existing), Redis 7-alpine, Celery (worker)

**Storage**: PostgreSQL 15 (persistent via named volume), Redis 7 (in-memory, ephemeral)

**Testing**: Manual validation via `docker compose up`, health check endpoints, integration tests in CI

**Target Platform**: Linux Docker containers, modern web browsers (Chrome, Firefox, Edge)

**Project Type**: web-service (Django backend + React frontend)

**Performance Goals**: Full stack starts within 3 minutes on first run (SC-001); subsequent starts under 30 seconds (SC-002); Redis cache hit reduces API response time by 40% (SC-005)

**Constraints**: Ports 5432, 6379, 8000, 5173 must be free on the host; Docker must be installed

**Scale/Scope**: Local development infrastructure for up to 5 concurrent developers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| I | Multi-Tenancy | ✅ Not Applicable | Infrastructure layer — no data model changes |
| II | Accounting Integrity | ✅ Not Applicable | No financial logic affected |
| III | API Rules | ✅ Not Applicable | No API changes |
| IV | Code Standards | ✅ Not Applicable | No code changes to backend/frontend |
| V | AI Safety Rules | ✅ Not Applicable | AI safety is handled at application layer, not infra |
| VI | Security | ✅ Compliant | Redis in dev mode (no auth); not exposed to host |
| VII | Performance | ✅ Compliant | Redis aligns with async/caching requirement |
| VIII | MVP Discipline | ✅ Compliant | Feature is scoped to infra only; worker is opt-in |

**No violations found.** Constitution gates passed.

## Project Structure

### Documentation (this feature)

```text
specs/003-docker-compose-infrastructure/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
infra/
├── docker-compose.yml   # Updated: added Redis + worker profile
├── Dockerfile            # Updated: installs Celery + Redis deps
└── init-db.sql           # Unchanged

backend/
├── requirements/
│   ├── base.txt          # Unchanged (Redis driver already listed or NEEDS CHECK)
│   └── dev.txt           # May need redis + celery deps

frontend/
├── package.json          # Unchanged
└── vite.config.js        # May need proxy update for dev
```

**Structure Decision**: Infrastructure configuration stays in `infra/` as it already does. Backend requirements may need updates for Redis client (`redis-py`) and Celery dependencies. No new directories needed.

## Complexity Tracking

No constitutional violations to justify.

## Phase 0: Research

All decisions are clear from the feature specification and existing project structure. No NEEDS CLARIFICATION markers remain.

Key research findings consolidated in [research.md](./research.md).

## Phase 1: Design

### Data Model

No new data entities — this feature adds infrastructure services only. See [data-model.md](./data-model.md) for environment variable contracts.

### API Contracts

The feature does not introduce new API endpoints. See [contracts/](./contracts/) for inter-service communication contracts (hostnames, ports, env vars).

### Quickstart Validation

Validation guide in [quickstart.md](./quickstart.md).
