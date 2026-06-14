# Research: Project Foundation

**Phase**: 0 — Research & Unknown Resolution
**Feature**: [spec.md](./spec.md)

## Overview

All specification ambiguities were resolved during the clarify phase. No NEEDS CLARIFICATION markers remained in the spec. This document consolidates the decisions and their rationale.

## Technology Decisions

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| Backend Framework | Django 5.x + DRF | Per constitution Article IV. Mature, secure, excellent ORM and admin. Built-in auth system. | FastAPI (less mature ecosystem, no built-in admin) |
| Database | PostgreSQL 15+ | Per implementation plan. UUID support, JSON fields, robust multi-tenant support. | MySQL (weaker JSON support, no native UUID) |
| Auth Protocol | JWT (simplejwt) | Per constitution Article VI. Stateless, standard for SPA + REST API. | Session-based (requires CSRF, less SPA-friendly) |
| Password Hashing | bcrypt (via Django) | Per constitution Article VI. Industry standard. | Argon2 (stronger but Django's bcrypt is sufficient for MVP) |
| Testing | pytest + DRF APITestCase | Per spec decisions. Industry standard for Django REST projects. | Django TestCase (less flexible) |
| Containerization | Docker + Docker Compose | Per implementation plan. Consistent dev/prod parity. | Manual setup (inconsistent, error-prone) |
| Frontend | React | Per implementation plan. Component-based, large ecosystem. | Vue, Svelte (equally valid, React chosen for availability) |

## Multi-Tenancy Approach

| Decision | Choice |
|----------|--------|
| Strategy | Shared database, tenant_id isolation (per constitution) |
| Enforcement | Middleware extracts tenant, overrides default queryset |
| Tenant Resolution | After login — user picks tenant (from clarifications) |

## Session & Auth Decisions

| Decision | Choice |
|----------|--------|
| Session Duration | 24 hours default, 30 days with "remember me" |
| Token Type | JWT access + refresh token pair |
| Password Reset | Email-based with token, no SMS fallback for MVP |
| Email Verification | Not required for MVP (from spec) |

## User & Tenant States

| Entity | States | Transition Triggers |
|--------|--------|-------------------|
| User | Active, Invited/Pending, Disabled | Registration → Active; Invitation → Pending; Admin action → Disabled |
| Tenant | Active, Suspended, Cancelled | Registration → Active; Non-payment → Suspended; Admin/System → Cancelled |

## Key Constraints

- All tables include `tenant_id` (non-negotiable, constitution Article I)
- No query allowed without tenant filtering
- Passwords hashed with bcrypt
- JWT required for all endpoints except register/login/password-reset
- Service layer pattern required — no business logic in views
