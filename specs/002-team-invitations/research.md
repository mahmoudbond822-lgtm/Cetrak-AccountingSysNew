# Research: Team Invitations

**Phase**: 0 — Research & Unknown Resolution
**Feature**: [spec.md](./spec.md)

## Overview

All specification ambiguities were resolved during the clarify phase. No NEEDS CLARIFICATION markers exist. This document consolidates the decisions and their rationale.

## Key Clarifications

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Existing user notification | Passive — new tenant appears on next login | No notification infrastructure for MVP; aligns with independent test criteria |
| Duplicate pending invitations | Rejected with error | Admin must cancel existing invitation before creating a new one |
| Invitation expiry | 7 days from creation | Industry standard for team invitations |
| Token generation | Secure random token (Django's `get_random_string` or `secrets.token_urlsafe`) | No need for JWT-based tokens — simple opaque token suffices |

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Service layer | InvitationService + TeamService | Keeping with established pattern (Constitution Article IV) |
| Invitation model | TenantScopedModel (tenant FK) | Consistent with data model design (Constitution Article I) |
| Team endpoints | All under `/api/v1/tenants/` | Consistent with existing URL structure |
| Admin enforcement | DRF permission class | Reusable pattern across all admin endpoints |
| Registration modification | Optional invitation_token parameter | Minimal change to existing register flow |

## Key Constraints

- All team endpoints require admin role (FR-010)
- Last admin protection enforced at service layer (FR-009)
- Invitation token single-use with 7-day expiry
- Existing user does not re-register — Membership created directly
