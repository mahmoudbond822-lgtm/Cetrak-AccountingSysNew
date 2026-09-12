# Implementation Plan: 012-H2 Identity & Session Hardening

## Goal

Resolve AUD-008, AUD-009, AUD-017 and the user-disable gap on `012-inventory` without creating Feature 013 or touching deferred P2/P3 items.

## Approach

Four independent phases, each with implementation + tests. Backend first, then the frontend contract migration, then full regression + Spec-Kit close-out.

## Phases

### H2-1 — Invitation email binding
- Add `_email_key` canonicalizer in `accounts/services.py`.
- `create_invitation` stores canonical email; `accept_invitation` validates binding; `register_view` rejects mismatch pre-creation.
- Tests: match (case/whitespace variants), mismatch (no user created, invitation reusable), stored-canonical, no-email-reveal, audited.

### H2-2 — Refresh cookie + CSRF + CSP
- New `accounts/cookies.py` (refresh + CSRF helpers, `csrf_invalid`).
- `login`/`register`/`refresh`/`logout` rewritten to cookie flow; refresh body response dropped.
- Settings: base refresh-cookie config + `CONTENT_SECURITY_POLICY`; dev credentials CORS; prod secure cookie + origins + header allowlist + `SecurityHeadersMiddleware`.
- Frontend: `api.js` single-flight cookie refresh, `X-CSRFToken`, no refresh token stored; pages store access only.
- Tests: `test_refresh_cookie_csrf.py` (10), `test_security_headers.py` (2); migrate `test_auth_api.py` to helpers.

### H2-3 — Tenant-switch session continuity
- `tenant_switch_view` blacklists current refresh, mints target-scoped refresh, sets cookie, audits `tenant.switch` (from/to via access-token claim).
- Tests: `test_tenant_switch_session.py` (12) incl. bound/unbound, chain switch-back, no-rewind, suspension/disabled gates.

### H2-4 — Operator user-disable
- `TeamService.set_user_status` + last-admin guard; `member_status_update_view`; status read-only in `UserSerializer`; route `tenant-member-status`.
- Frontend Team page Enable/Disable.
- Tests: `test_user_disable_api.py` (11); migrate `test_status_enforcement.py` refresh to cookie.

## Close-out
- Full suite green (367/1); migrations clean; build clean; lint 16 unchanged.
- Write `specs/012-hardening-h2/*` + `docs/audits/production-hardening-h2-report-001.md`; update AGENTS.md; commit `fix: harden identity and tenant session security`; no push/deploy.