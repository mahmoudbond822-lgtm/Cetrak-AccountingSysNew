# Implementation Report: 012-H2 Identity & Session Hardening

## Status

**Complete.** All four objectives implemented, tested, and verified. Full suite green.

## Outcome summary

| Objective | Deliverable | Tests |
|---|---|---|
| H2-1 Invitation binding | canonical email key + pre-creation rejection | `test_invitation_binding.py` (8) |
| H2-2 Refresh cookie + CSRF + CSP | HttpOnly refresh cookie, double-submit CSRF, prod CSP/security headers | `test_refresh_cookie_csrf.py` (10), `test_security_headers.py` (2) |
| H2-3 Switch session continuity | refresh rotated + scoped on switch, audited from/to | `test_tenant_switch_session.py` (12) |
| H2-4 Operator user-disable | admin status endpoint, last-admin guard, read-only `me.status`, UI | `test_user_disable_api.py` (11) |

## Regression

- Backend: 367 passed / 1 postgres-only skip (baseline 324, +43).
- Migrations: "No changes detected".
- Frontend: build clean; lint unchanged at 16 pre-existing (0 new).

## How each AUD-002 condition was closed

| AUD-002 condition | Id |
|---|---|
| Invitation email binding (P2) | AUD-008 |
| Refresh token storage + CSRF + CSP (P2) | AUD-009 |
| Switch/refresh tenant-context drift (P2) | AUD-017 |
| Operator disable path + `me` status write (P2/P3) | AUD-021 user-disable facet |

## Notable decisions

- `from_tenant_id` on `tenant.switch` reads the **access-token claim** (`request.auth`), because the tenant-resolution middleware deliberately nulls `request.tenant_id` on switch paths. Single-tenant logins that still bind tenant → the source is the current access tenant.
- Refresh/logout carry CSRF; login is protected by SameSite=Lax and switch by the Authorization header — the single documented authoritative flow.
- `User.status` is **global** (account-level disable) by existing data model; per-tenant removal stays on `DELETE /tenants/members/{id}/`.
- Prod-only `SecurityHeadersMiddleware` keeps dev/test tooling unaffected and avoids CSP breakage in the CORS-less dev flow.

## Files

See `docs/audits/production-hardening-h2-report-001.md` §4 (15 files, 1 backend test package + 1 frontend).

## Constitution impact

No product scope; no deferred work pulled in; contracts changed only where hardening requires (documented §10 of the report); audit stays in the service layer.