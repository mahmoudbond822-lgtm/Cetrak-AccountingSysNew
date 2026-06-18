# Implementation Plan: Multi-Tenancy Hardening

**Branch**: `004-multi-tenancy-hardening` | **Date**: 2026-06-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-multi-tenancy-hardening/spec.md`

## Summary

Harden the existing multi-tenancy layer with active middleware validation (FR-001–FR-004), a required non-null tenant FK on `TenantScopedModel` (FR-006), a database index on `Membership.tenant_id` (FR-005), and an explicit `for_tenant()` query method for all tenant-scoped queries (FR-007). This is a zero-new-feature infrastructure pass — no models, endpoints, or UI are added.

## Technical Context

**Language/Version**: Python 3.14 (from project `pyproject.toml`), Django 6.0.4

**Primary Dependencies**: Django REST Framework, psycopg2-binary (PostgreSQL adapter)

**Storage**: PostgreSQL 15+ (production), SQLite :memory: (tests)

**Testing**: pytest 9.x + pytest-django, DRF APITestCase; 36 existing tests must continue to pass

**Target Platform**: Linux Docker containers, modern web browsers (Chrome, Firefox, Edge)

**Project Type**: web-service (Django backend + React frontend)

**Performance Goals**: Tenant-filtered membership queries <50ms at 10k-member scale (SC-002); cross-tenant rejection <200ms (SC-001)

**Constraints**: Constitution Articles I and VI require tenant isolation at both DB and app layer; every existing test must remain green (SC-005)

**Scale/Scope**: 50 users/tenant MVP, single-region deployment; only existing tenant-scoped models (Invitation) and Membership are affected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| I | Multi-Tenancy | ✅ Compliant | Strengthens enforcement via active middleware + non-null FK + explicit scoping |
| II | Accounting Integrity | ✅ Not Applicable | No financial logic affected |
| III | API Rules | ✅ Compliant | 403 error format follows existing conventions |
| IV | Code Standards | ✅ Compliant | All logic stays in services layer; middleware is infrastructure |
| V | AI Safety Rules | ✅ Not Applicable | No AI-generated content in this feature |
| VI | Security | ✅ Compliant | Active tenant validation directly implements isolation mandate |
| VII | Performance | ✅ Compliant | Adding index on `tenant_id` satisfies the optimization requirement |
| VIII | MVP Discipline | ✅ Compliant | Scoped to hardening only; no scope creep |

**No violations found.** Constitution gates passed.

## Project Structure

### Documentation (this feature)

```text
specs/004-multi-tenancy-hardening/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── accounts/
│   │   ├── models.py       # Membership.tenant db_index, Invitation.tenant NOT NULL
│   │   ├── services.py     # Use .for_tenant() in all tenant-scoped queries
│   │   └── permissions.py  # No change (already correct)
│   ├── core/
│   │   ├── models.py       # TenantScopedModel: null=False + TenantScopedQuerySet.for_tenant()
│   │   └── middleware.py   # Rewrite: active validation, UUID parsing, JWT-first resolution
│   └── ── migrations/      # 2 new migrations (NOT NULL, db_index)
├── config/
│   └── settings/
│       └── test.py         # No change (SQLite test DB unaffected)
└─── tests/                 # Existing 36 tests unchanged
```

**Structure Decision**: All changes are within existing backend files. No new files, directories, or apps are created. The infrastructure path is unchanged.

## Complexity Tracking

No constitutional violations to justify.

## Phase 0: Research

No NEEDS CLARIFICATION markers exist in the spec. All decisions are clear from the existing codebase, constitution, and spec. Key findings consolidated in [research.md](./research.md).

## Phase 1: Design

### Data Model

Only two schema changes. See [data-model.md](./data-model.md) for full details.

| Change | Entity | Field | Action |
|--------|--------|-------|--------|
| 1 | Invitation (via TenantScopedModel) | tenant | `null=True` → `null=False` |
| 2 | Membership | tenant | Add `db_index=True` |

### API Contracts

The feature does not introduce new API endpoints or change existing response shapes. Error responses from middleware return 403 with a `{"detail": "..."}` body, matching the existing error format. See [contracts/](./contracts/) for error contract documentation.

### Quickstart Validation

Validation guide in [quickstart.md](./quickstart.md) — 5 runnable scenarios covering middleware enforcement, index behaviour, NOT NULL constraint, `for_tenant()` usage, and test suite regression.
