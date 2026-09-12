# Implementation Tasks: 012-H2 Identity & Session Hardening

Status per task: `[x]` complete (implementation close-out).

## Phase H2-1 — Invitation email binding

- [x] `_email_key(email) = str(email or "").strip().lower()` in `accounts/services.py`.
- [x] `create_invitation` stores the canonical email key.
- [x] `accept_invitation` validates `_email_key(user) == _email_key(invitation)`; generic mismatch message (no email echo).
- [x] `register_view` rejects mismatched invitations before attempting user creation.
- [x] Tests (`test_invitation_binding.py`, 8): match; case + whitespace variation; mismatch (no user-left-behind, invitation reusable); stored canonical key; no-email-reveal; audited accept.

## Phase H2-2 — Refresh token cookie + CSRF + CSP

- [x] `accounts/cookies.py`: `refresh_cookie_kwargs`, `set_refresh_cookie`, `delete_refresh_cookie`, `set_csrf_cookie`, `csrf_invalid`.
- [x] Login/register set refresh + CSRF cookies; `refresh` removed from response bodies.
- [x] `refresh_view` cookie-based (no body token), rotates, returns `{access}` only; disabled user 403.
- [x] `logout_view` cookie-based, revokes + clears, 205.
- [x] CSRF required on refresh/logout (`HTTP_X_CSRFTOKEN` vs masked cookie, `compare_digest`, 403 on mismatch).
- [x] Settings: base `REFRESH_COOKIE_*` + `CONTENT_SECURITY_POLICY`; dev `CORS_ALLOW_CREDENTIALS`; prod `REFRESH_COOKIE_SECURE=True`, credential origins, `x-csrf-token`/`x-tenant-id` allowlist, `DJANGO_CSP_CONNECT_SRC`.
- [x] `SecurityHeadersMiddleware` in `core/middleware.py` (CSP not overwriting existing, nosniff, Referrer-Policy, Permissions-Policy); registered in prod only.
- [x] Frontend `api.js`: instance `withCredentials`, `readCookie`/`csrfToken`, single-flight cookie refresh, no refresh-token storage, `setTokens(access)`.
- [x] Frontend pages updated: Login, Register (access only), Dashboard logout (CSRF), TenantSwitcher (access only).
- [x] Tests (`test_refresh_cookie_csrf.py`, 10): cookie attrs incl. max-age; refresh via cookie; no-cookie 401; no/wrong CSRF 403; logout clears + 205; remember-me 30d lifetime; prod secure-kwargs test (env + module reload); `test_security_headers.py` (2).
- [x] `test_auth_api.py` migrated to cookie flow via `helpers.py`.

## Phase H2-3 — Tenant-switch session continuity

- [x] `tenant_switch_view` blacklists current refresh cookie jti + mints target-scoped refresh, sets cookie.
- [x] Audit `tenant.switch` with `from_tenant_id` (from access-token claim) / `to_tenant_id`.
- [x] Tests (`test_tenant_switch_session.py`, 12): multi-tenant unbound initial tokens; rotation on refresh; switch-bind; repeated refresh stability; chain switch-back (from B → to A); old access blacklisted after switch; old refresh cannot rewind; single-tenant binding; suspended-tenant 403; disabled user 401; audited from/to; no-membership 404/403.

## Phase H2-4 — Operator user-disable

- [x] `TeamService.set_user_status` with last-admin guard; audit `member.disable`/`member.enable`.
- [x] `PATCH /tenants/members/{user_id}/status/` (`MemberStatusSerializer`, route `tenant-member-status`); 404 cross-tenant; Admin-only.
- [x] `UserSerializer.status` read-only (kills `me` self PATCH).
- [x] Frontend `TeamPage.jsx`: Enable/Disable with confirmation + error surfacing.
- [x] Tests (`test_user_disable_api.py`, 11): disable → login 403 / existing access 401 / refresh 403 / switch 401; re-enable restores; last-admin guard 400; member sees no action (403/404); audit rows; `me` PATCH status ignored (200, unchanged); disable updates global status.
- [x] `test_status_enforcement.py` refresh moved to cookie flow.

## Close-out

- [x] Full backend suite green (**367 passed, 1 postgres-only skip**; baseline 324 + 43 new).
- [x] `makemigrations --check --dry-run` → "No changes detected".
- [x] `npm run build` clean (399.52 kB JS / 110.36 kB gzip); `npm run lint` still exactly 16 pre-existing problems (zero new).
- [x] `specs/012-hardening-h2/*` artifacts written.
- [x] `docs/audits/production-hardening-h2-report-001.md` written.
- [x] AGENTS.md status updated.
- [x] Working-tree diff inspected; only hardening-scoped changes staged; committed as `fix: harden identity and tenant session security`. No push, no deploy, no Feature 013.