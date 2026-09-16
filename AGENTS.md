<!-- SPECKIT START -->
Implementation plan: specs/013-auto-customer-code/plan.md | specs/014-auto-customer-code/plan.md | specs/015-auto-vendor-code/plan.md

Current phase: 012-H2 IDENTITY & SESSION HARDENING COMPLETE — resolved AUD-008 (invitation email binding), AUD-009 (refresh token moved to HttpOnly cookie + double-submit CSRF + restrictive CSP/security headers in prod), AUD-017 (tenant-switch rotates the refresh cookie, no tenant-context drift on refresh), and the operator user-disable gap (`PATCH /tenants/members/{id}/status/`, last-admin guard, `me` status read-only). Features 001–012 remain implemented. Full suite 367 passed, 1 postgres-only skip, migrations clean, frontend build green, lint unchanged (16 pre-existing problems). Do not push or deploy.

## What This Phase Does

Hardens the identity/session layer per AUD-002 (`docs/audits/production-readiness-re-audit-002.md` gap → report at `docs/audits/production-hardening-h2-report-001.md`, 79/100 READY WITH CONDITIONS baseline) without creating Feature 013:
- **H2-1 (AUD-008)** `_email_key` canonical binding: invitations stored canonical; acceptance rejects a different email before any user is created; generic message (no enumeration); invitation stays reusable.
- **H2-2 (AUD-009)** Refresh token leaves localStorage → HttpOnly `refresh_token` cookie (path `/api/v1/`, SameSite=Lax, Secure forced in prod, max-age = 7d/30d remember-me) and is removed from all response bodies. `/auth/refresh/` + `/auth/logout/` require double-submit CSRF (masked `csrftoken` cookie vs `X-CSRFToken`, constant-time). Prod emits a restrictive CSP + nosniff/Referrer-Policy/Permissions-Policy via `SecurityHeadersMiddleware`.
- **H2-3 (AUD-017)** `tenant_switch` blacklists the current refresh cookie and lands a new one scoped to the target tenant; refresh always mints from the cookie's own claims so tenant context survives rotation; old refreshes cannot rewind; `tenant.switch` audited with source/target.
- **H2-4 (Operator user-disable)** `TeamService.set_user_status` + `PATCH /tenants/members/{id}/status/` (Admin, tenant-scoped 404, last-admin guard, audited `member.disable`/`member.enable`); `UserSerializer.status` read-only so `me` can no longer self-disable; Team UI Enable/Disable. Disable is global (account-level); per-tenant removal stays on the existing DELETE.

## Generated Artifacts

- `docs/audits/production-hardening-h2-report-001.md` — Authoritative H2 hardening report (baseline, findings, implementation, files, contracts, regression, readiness, next steps)
- `specs/012-hardening-h2/spec.md` — H2 specification (implemented)
- `specs/012-hardening-h2/plan.md` — Implementation plan, phases H2-1…H2-4 (implemented)
- `specs/012-hardening-h2/tasks.md` — Implementation tasks (all complete)
- `specs/012-hardening-h2/quickstart.md` — Manual browser verification (cookies, CSRF, switch, invitation binding, disable)
- `specs/012-hardening-h2/checklists/requirements.md` — Spec quality checklist (verified at close-out)
- `specs/012-hardening-h2/report.md` — Implementation report

## Key Decisions (locked in the plan)

- `from_tenant_id` on `tenant.switch` reads the **access-token claim** (`request.auth.get("tenant_id")`), since `TenantResolutionMiddleware` deliberately nulls `request.tenant_id` on switch paths; unbound (multi-tenant-login) sessions honestly record `None`.
- One authoritative CSRF flow: double-submit on the cookie-consuming endpoints (refresh/logout); login/register rely on SameSite=Lax (no ambient session yet) and switch on the Authorization header.
- Access token remains in localStorage — the documented residual (HttpOnly+credential redesign stays deferred/out-of-scope).
- `User.status` disable is **global** per the data model; per-tenant removal unchanged.
- `SecurityHeadersMiddleware` is prod-only so dev/test tooling is untouched.
- Contract change (no `refresh` in bodies) adopted deliberately and everything affected migrated in the same commit.

## Next Steps (after review)

- Review the H2 hardening report and `specs/012-hardening-h2/*`. Remaining P2 (AUD-010, 011, 012, 015, 025, 026) and P3 (019, 023, 027, 029 + access-token granularity observations) are documented for future phases — natural next candidates: AUD-025 bcrypt, AUD-026 Celery. Do not push or deploy; commit via the auto-commit hook only.

## Quick Reference

- Backend tests: `cd backend && $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q` → 367 passed, 1 postgres-only skip (324 baseline + 8 invitation-binding + 10 refresh-cookie/CSRF + 12 tenant-switch-session + 11 user-disable + 2 security-headers)
- New backend pieces: `apps/accounts/cookies.py`, `_email_key` + `TeamService.set_user_status` in `apps/accounts/services.py`, status route `tenant-member-status`, `SecurityHeadersMiddleware` in `apps/core/middleware.py`
- Frontend changed files: `src/services/api.js` (cookie refresh + CSRF header, single-flight, no refresh storage), `src/pages/{LoginPage,RegisterPage,DashboardPage,TeamPage}.jsx`, `src/components/Layout/TenantSwitcher.jsx`
- Migrations: `py manage.py makemigrations --check --dry-run` → "No changes detected" (behavior+config only)
- Frontend: `npm run build` clean (399.52 kB JS / 110.36 kB gzip); `npm run lint` still exactly 16 pre-existing problems (zero new)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->