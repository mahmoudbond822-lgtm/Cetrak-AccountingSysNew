# Implementation Plan: Project Foundation

**Branch**: `001-project-foundation` | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-project-foundation/spec.md`

## Summary

Establish the foundational infrastructure for the Cetrak ERP system: Django project setup, Docker containerization, PostgreSQL database, multi-tenancy data model, JWT-based authentication, and user registration/login flows. This is the gate all other features depend on.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Django 5.x, Django REST Framework, djangorestframework-simplejwt, psycopg2-binary, python-decouple, django-filter

**Storage**: PostgreSQL 15+ with UUID extension

**Testing**: pytest, pytest-django, DRF APITestCase

**Target Platform**: Linux (Docker container), modern web browsers (Chrome, Firefox, Edge)

**Project Type**: web-service (Django backend + React frontend)

**Performance Goals**: Login completes within 5 seconds (SC-002); registration completes within 3 minutes (SC-001); page loads under 2 seconds

**Constraints**: Every table must include tenant_id with mandatory tenant filtering enforced via middleware (constitution Article I); JWT authentication required for all endpoints (constitution Article VI); service layer pattern required — no business logic in views (constitution Article IV)

**Scale/Scope**: 50 users per tenant in MVP; single-region deployment; global audience with initial Egypt focus

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| I | Multi-Tenancy | ✅ Compliant | tenant_id on every table, middleware enforcement planned |
| III | API Rules | ✅ Compliant | RESTful endpoints, JWT auth, consistent JSON |
| IV | Code Standards | ✅ Compliant | Django + DRF, services layer planned |
| VI | Security | ✅ Compliant | JWT + bcrypt + tenant isolation planned |
| VII | Performance | ✅ Compliant | No heavy async tasks needed for Foundation; indexes planned |
| VIII | MVP Discipline | ✅ Compliant | Feature scoped to Foundation only |

**No violations found.** Constitution gates passed.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-foundation/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py          # BaseModel, Tenant
│   │   ├── middleware.py       # Tenant resolution middleware
│   │   └── admin.py
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── models.py          # User, Membership
│   │   ├── serializers.py
│   │   ├── services.py        # Auth service, Invitation service
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   ├── accounting/            # (future features)
│   ├── sales/                 # (future features)
│   └── purchases/             # (future features)
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── pytest.ini
└── Dockerfile

frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── LoginForm.jsx
│   │   │   └── RegisterForm.jsx
│   │   └── Layout/
│   │       ├── TenantSwitcher.jsx
│   │       └── ProtectedRoute.jsx
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── DashboardPage.jsx
│   │   └── TenantSelectPage.jsx
│   ├── services/
│   │   └── api.js
│   ├── hooks/
│   ├── App.jsx
│   └── index.jsx
├── package.json
└── .env

infra/
├── docker-compose.yml
├── Dockerfile
└── .github/workflows/
```

**Structure Decision**: Web application with separate `backend/` (Django) and `frontend/` (React) directories. The backend follows Django's app-based modular structure with a services layer in each app.

## Complexity Tracking

No constitutional violations to justify. Foundation feature is straightforward.

## Phase 0: Research

*All decisions resolved in spec clarifications. No NEEDS CLARIFICATION markers remain in the spec.*

Key research findings consolidated in [research.md](./research.md).

## Phase 1: Design

### Data Model

Detailed entity definitions in [data-model.md](./data-model.md).

Core entities:
- **Tenant**: id (UUID), name, status (Active/Suspended/Cancelled), created_at, updated_at
- **User**: id (UUID), email (unique), password (hashed), display_name, status (Active/Invited/Disabled), created_at, updated_at
- **Membership**: id (UUID), user_id (FK), tenant_id (FK), role (Admin/Accountant/Manager), created_at, updated_at
- **Invitation**: id (UUID), tenant_id (FK), email, role, token, expires_at, accepted_at, created_at

### API Contracts

Detailed contracts in [contracts/](./contracts/). Core endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Register new user + tenant |
| POST | /api/v1/auth/login | Log in with email + password |
| POST | /api/v1/auth/logout | Log out (invalidate token) |
| POST | /api/v1/auth/refresh | Refresh JWT token |
| POST | /api/v1/auth/password-reset/request | Request password reset email |
| POST | /api/v1/auth/password-reset/confirm | Confirm password reset with token |
| GET | /api/v1/auth/me | Get current user profile |
| PATCH | /api/v1/auth/me | Update current user profile |
| GET | /api/v1/tenants/current | Get current tenant info |
| GET | /api/v1/tenants/members | List tenant members (admin) |
| POST | /api/v1/tenants/invitations | Invite new member (admin) |
| GET | /api/v1/tenants/switch/{tenant_id} | Switch active tenant |

### Quickstart Validation

Validation guide in [quickstart.md](./quickstart.md).

## Phase 2: Tasks

Task generation delegated to `/speckit.tasks` command. Output in [tasks.md](./tasks.md).
