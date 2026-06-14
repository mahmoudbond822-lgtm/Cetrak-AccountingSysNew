# Implementation Plan: Team Invitations

**Branch**: `002-team-invitations` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-team-invitations/spec.md`

## Summary

Admins can invite new members by email, manage team members (roles, removal), and cancel invitations. The feature extends the existing accounts app with an Invitation model, invitation/team services, team management API endpoints, and a frontend team management page.

## Technical Context

**Language/Version**: Python 3.11+, Django 5.x/6.x (as installed)

**Primary Dependencies**: Django REST Framework, djangorestframework-simplejwt (existing)

**Storage**: PostgreSQL 15+ (existing via foundation setup)

**Testing**: pytest, pytest-django, DRF APITestCase (existing)

**Target Platform**: Linux (Docker container), modern web browsers (Chrome, Firefox, Edge)

**Project Type**: web-service (Django backend + React frontend)

**Performance Goals**: Team management operations respond within 2 seconds (SC-004); invitation flow completes within 30 seconds for admin (SC-001)

**Constraints**: Admin-only access for all team endpoints (FR-010, Constitution Article VI); last-admin protection (FR-009); tenant-isolated data (Constitution Article I)

**Scale/Scope**: 50 users per tenant in MVP (existing); this feature adds invitation management for those users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| I | Multi-Tenancy | ✅ Compliant | Invitation is TenantScopedModel (tenant FK); team APIs scoped by X-Tenant-ID |
| III | API Rules | ✅ Compliant | RESTful endpoints, JWT auth, consistent JSON error format |
| IV | Code Standards | ✅ Compliant | Django + DRF, dedicated services layer (InvitationService, TeamService) |
| VI | Security | ✅ Compliant | Admin-only endpoints enforced via permission checks; secure random tokens |
| VII | Performance | ✅ Compliant | Indexes on token, email, tenant_id; no heavy async needed |
| VIII | MVP Discipline | ✅ Compliant | Feature scoped to team invitations only; no notification infrastructure |

**No violations found.** Constitution gates passed.

## Project Structure

### Documentation (this feature)

```text
specs/002-team-invitations/
├── plan.md              # This file
├── spec.md              # Feature specification
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
│   └── accounts/
│       ├── models.py          # + Invitation model (TenantScopedModel)
│       ├── services.py        # + InvitationService, TeamService
│       ├── serializers.py     # + InvitationSerializer, MemberSerializer, RoleChangeSerializer
│       ├── views.py           # + Invitation views, Member views
│       ├── urls.py            # + Team management routes
│       └── tests/
│           └── test_team_api.py  # New test file for team endpoints

frontend/
├── src/
│   ├── components/
│   │   └── Layout/
│   │       └── TenantSwitcher.jsx  # + Tenant display/switch
│   ├── pages/
│   │   └── TeamPage.jsx        # New page
│   └── App.jsx                 # + TeamPage route
```

**Structure Decision**: Web application with separate `backend/` (Django) and `frontend/` (React). This feature lives entirely within the existing `accounts` app, extending models, services, and views. No new Django apps needed.

## Complexity Tracking

No constitutional violations to justify. Feature is a straightforward extension of the existing accounts module.

## Phase 0: Research

*All decisions resolved in spec clarifications. No NEEDS CLARIFICATION markers remain in the spec.*

Key research findings consolidated in [research.md](./research.md).

## Phase 1: Design

### Data Model

Detailed entity definitions in [data-model.md](./data-model.md).

New entity:
- **Invitation** (inherits TenantScopedModel): tenant (FK), email, role, token (unique), expires_at, accepted_at

### API Contracts

Detailed contracts in [contracts/](./contracts/). New endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/tenants/invitations | Create invitation (admin) |
| GET | /api/v1/tenants/invitations | List pending invitations (admin) |
| DELETE | /api/v1/tenants/invitations/{id} | Cancel invitation (admin) |
| GET | /api/v1/tenants/members | List members (admin) |
| PATCH | /api/v1/tenants/members/{user_id}/role | Change member role (admin) |
| DELETE | /api/v1/tenants/members/{user_id} | Remove member (admin) |
| POST | /api/v1/tenants/switch/{tenant_id} | Switch active tenant |

Existing endpoints modified:
- POST /api/v1/auth/register — accepts optional `invitation_token` parameter

### Quickstart Validation

Validation guide in [quickstart.md](./quickstart.md).

## Phase 2: Tasks

Task generation delegated to `/speckit.tasks` command. Output in [tasks.md](./tasks.md).
