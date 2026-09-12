# Spec: 012-H2 Identity & Session Hardening

- **ID**: 012-H2
- **Status**: Implemented (2026-09-12)
- **Parent**: Feature 012 lineage — continuation of Production Hardening, constrained to P2/P3 identity+session findings from AUD-002
- **Branch**: `012-inventory`

## Scope

Four objectives, and only four:

1. **H2-1 — Invitation email binding (AUD-008, P2)**: an invitation token may only be accepted by the email address it was sent to (case-insensitive, whitespace-insensitive canonical binding).
2. **H2-2 — Refresh token cookie + CSRF + CSP (AUD-009, P2)**: move the refresh token out of localStorage into an HttpOnly cookie; secure the cookie-consuming endpoints with double-submit CSRF; emit a restrictive CSP and security headers in prod.
3. **H2-3 — Tenant-switch session continuity (AUD-017, P2)**: switching tenants rotates the refresh cookie so the session's tenant context survives refresh and old refreshes can't rewind a session.
4. **H2-4 — Operator user-disable provisioning**: admin self-service to disable/re-enable members with last-admin guard; make `me`'s `status` read-only so users cannot self-disable or self-enable.

Explicitly out of scope (documented, not implemented): access-token redesign/storage, refresh `token_type` claim verification, bcrypt (AUD-025), Celery/async (AUD-026), pagination (AUD-029), AUD-010/011/012/015/019/023/027, everything else in AUD-002 P2/P3, and any Feature 013.

## Requirements

### R1 (H2-1)
- R1.1 Invitations store a canonical email key.
- R1.2 Accepting an invitation validates `_email_key(user_email) == _email_key(invitation_email)`.
- R1.3 Mismatch rejects the flow **before** user creation and leaves the invitation reusable.
- R1.4 The rejection message leaks no email addresses.

### R2 (H2-2)
- R2.1 Refresh token never appears in any API response body.
- R2.2 Refresh cookie is HttpOnly, path `=/api/v1/`, SameSite=Lax, presence enforced; `Secure` forced in prod.
- R2.3 `POST /auth/refresh` and `POST /auth/logout` require double-submit CSRF (`X-CSRFToken` vs masked `csrftoken` cookie), compare in constant time.
- R2.4 Prod responses include a restrictive CSP (no `'unsafe-inline'`) plus nosniff/Referrer-Policy/Permissions-Policy; dev/test unaffected.
- R2.5 Access cookie in localStorage is the documented residual (out of scope).

### R3 (H2-3)
- R3.1 On switch, the current refresh cookie is revoked and a new one scoped to the target tenant replaces it.
- R3.2 Refresh always mints from the cookie's own claims so tenant context survives rotation.
- R3.3 Switch records an audit row with source and target tenant.

### R4 (H2-4)
- R4.1 `PATCH /tenants/members/{user_id}/status/` (admin, tenant-scoped 404) sets Active/Disabled.
- R4.2 Last-active-admin cannot be disabled.
- R4.3 `UserSerializer.status` is read-only; `me` PATCH cannot change it.
- R4.4 Disable is global (account-level) and enforced at login, on-request, and on refresh; per-tenant removal kept on the existing DELETE.
- R4.5 Disable/enable audited (`member.disable`/`member.enable`).

## Contracts

Covered in `docs/audits/production-hardening-h2-report-001.md` §10. Net: bodies shrink (no `refresh`), refresh/logout gain CSRF + cookie inputs, switch rotates the cookie, new status endpoint.

## Verification

- Backend: 367 passed / 1 skipped (43 new).
- `makemigrations --check --dry-run` clean.
- `npm run build` clean; lint unchanged at 16 pre-existing.