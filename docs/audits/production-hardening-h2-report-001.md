# Identity & Session Hardening Report — Cetrak Accounting System

- **Report ID**: PROD-HARDENING-H2-001
- **Date**: 2026-09-12
- **Agency**: opencode (resolving AUD-002 → AUD-008, AUD-009, AUD-017 and the user-disable provisioning gap), verified by full regression
- **Scope**: Feature 012-H2 — Identity & Session Hardening, four objectives only
- **Constraint honored**: Feature 013 not created; no deferred P2/P3 work; no push; no deploy

---

## 1. Baseline

| Artefact | AUD-002 baseline (branch `012-inventory`, HEAD `bae9c12`) | After 012-H2 (working tree) |
|---|---|---|
| Backend suite | 324 passed, 1 postgres-only skip | **367 passed, 1 postgres-only skip (+43)** |
| Migrations drift | clean | `makemigrations --check --dry-run` → "No changes detected" |
| Frontend build | clean (399.05 kB JS / 110.26 kB gzip) | clean (vite 8.0.16, 130 modules, 399.52 kB JS / 110.36 kB gzip) |
| Frontend lint | 16 problems (15 errors, 1 warning) | **16 problems — identical, all pre-existing, zero new** |
| Refresh token location | localStorage (XSS-readable) | **HttpOnly cookie** `refresh_token`, path `/api/v1/`, SameSite=Lax, Secure in prod |
| Refresh token exposure | returned in login/refresh response bodies | **removed from all response bodies** — cookie is authoritative |
| CSRF protection on state-changing auth flows | none | **double-submit CSRF** (masked `csrftoken` cookie + `X-CSRFToken` header) on `/auth/refresh/` and `/auth/logout/` |
| CSP / security headers | none | restrictive CSP + nosniff + Referrer-Policy + Permissions-Policy in prod |
| Tenant-switch refresh | untouched (kept old refresh) | rotated refresh bound to target tenant; source/target audited |
| Invitation email binding | accepted by any email | **content-bound to the invited email** (case-insensitive, whitespace-stripped canonical key) |
| User disable path | none (me `PATCH` could even self-set status) | **`PATCH /tenants/members/{id}/status/`** (admin), status read-only on `me` |

AUD-002 was re-audited to **79/100 READY WITH CONDITIONS** before this feature began; its conditions map exactly to the four H2 objectives below.

---

## 2. Findings addressed

| ID | Finding | Severity | Resolution | Evidence |
|---|---|---|---|---|
| AUD-008 | Invitation token is content-neutral — any email can claim it | P2 | `_email_key(email) = str(email).strip().lower()`; invitations stored canonical at creation; `accept_invitation` re-checks `_email_key(user.email) == _email_key(invitation.email)`; `register_view` rejects mismatches **before** creating the user; generic error avoids enumeration | `accounts/services.py` (`_email_key`, `accept_invitation`, `create_invitation`), `accounts/views.py:register_view`, `test_invitation_binding.py` (8 tests) |
| AUD-009 | Refresh tokens stored in localStorage | P2 | Refresh moves to HttpOnly cookie: `refresh_token`, `max_age` = SimpleJWT lifetime (7d / 30d remember-me), `path=/api/v1/`, `SameSite=Lax`, `Secure` forced in prod; refresh removed from login/register/refresh bodies; frontend never reads a refresh token; single-flight refresh reads the cookie | `accounts/cookies.py`, `accounts/views.py` (login/refresh/logout), `config/settings/{base,dev,prod}.py`, `frontend/src/services/api.js`, `test_refresh_cookie_csrf.py` (10 tests) |
| AUD-009 (CSRF part) | Cookie auth without CSRF protection | P2 | Double-submit: login/register set a masked `csrftoken` cookie; `/auth/refresh/` and `/auth/logout/` require `X-CSRFToken` == cookie (const-time `compare_digest`), 403 on mismatch; login/switch rely on SameSite=Lax + Authorization header (documented rationale) | `accounts/cookies.py` (`set_csrf_cookie`, `csrf_invalid`), views, frontend api.js |
| AUD-009 (CSP part) | No content-security policy | P2 | Restrictive CSP emitted by `SecurityHeadersMiddleware` in prod: `default-src 'self'`, `script-src 'self'`, `style-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`, plus nosniff/Referrer-Policy/Permissions-Policy; `DJANGO_CSP_CONNECT_SRC` extends connect-src for cross-origin API hosts | `apps/core/middleware.py`, `settings/prod.py`, `test_security_headers.py` |
| AUD-017 | Access/refresh tenant context drifts after `tenant_switch` (refresh request lost tenant) | P2 | Switch blacklists the current refresh cookie, mints a new refresh scoped to the target, sets it on the cookie; `refresh_view` mints from the OLD cookie claims so the operator's tenant always survives rotation; switch emission audited (`action=tenant.switch`, from/to) | `accounts/views.py:tenant_switch_view`, `test_tenant_switch_session.py` (12 tests) |
| AUD-021 (partial) + audit finding | No operator path to disable a user; `me PATCH` could self-modify `status` | P2/P3 | `TeamService.set_user_status` (+ last-admin guard) exposed as `PATCH /tenants/members/{user_id}/status/` (Admin-only, tenant-scoped, 404 cross-tenant); `UserSerializer.status` is read-only so `me` cannot self-disable; disable is **global** (account-level) — per-tenant removal remains `DELETE /tenants/members/{id}/`; `member.disable`/`member.enable` audited | `accounts/services.py`, `accounts/views.py`, `accounts/serializers.py`, `accounts/urls.py`, `frontend/src/pages/TeamPage.jsx`, `test_user_disable_api.py` (11 tests) |

---

## 3. Implementation summary

### H2-1 — Invitation email binding (AUD-008)
- `_email_key` canonicalizes invite/registration emails (strip + lowercase) for content binding.
- `create_invitation` stores the canonical email (also makes the pending-uniqueness check case-insensitive).
- `accept_invitation` binds the token to the invited email; a user registering with a different address is refused even if the token is valid.
- `register_view` rejects the mismatch before attempting user creation (no throwaway user row), and the service re-checks inside the transaction (defense in depth).
- The invitation is left pending on failure → the correct invitee can still accept; no enumeration (generic wording, no email echo).

### H2-2 — Refresh token cookie + CSRF + CSP (AUD-009)
- New `accounts/cookies.py`: `refresh_cookie_kwargs` (config-driven name/path/secure/samesite + SimpleJWT-aligned `max_age`), `set_refresh_cookie`, `delete_refresh_cookie`, `set_csrf_cookie`, `csrf_invalid`.
- Login/register set the refresh cookie and a masked CSRF cookie; the refresh token is **never** in the response body.
- Refresh consumes **only** the HttpOnly cookie (rotates it + returns just `access`); logout revokes the cookie's token and clears it; both enforce CSRF.
- Prod forces `REFRESH_COOKIE_SECURE = True`, `CORS_ALLOW_CREDENTIALS = True` with explicit origins and `x-csrf-token`/`x-tenant-id` allowed headers; dev enables credentials with allow-all (documented dev-only footgun).
- `SecurityHeadersMiddleware` emits the restrictive CSP plus security headers on prod responses.

### H2-3 — Tenant-switch session continuity (AUD-017)
- `tenant_switch_view` blacklists the present refresh cookie, mints a refresh bound to the target tenant, and lands it on the cookie alongside the new access token.
- `refresh_view` rebuilds from the cookie's own claims → the switched tenant survives every rotation; an old (pre-switch) refresh is blacklisted and cannot rewind the session.
- Each switch records `tenant.switch` with source/target tenant and actor.

### H2-4 — Operator user-disable provisioning
- New admin endpoint with tenant-scoped lookup, last-admin guard, and audit; re-enable supported; disabled users are blocked at every boundary (login 403, existing access 401, refresh 403, switch 401).
- `me` can no longer change `status` (read-only in `UserSerializer`) — closing the self-disable/self-enable hole.
- Frontend Team page renders Enable/Disable with confirmation and error surfacing.

---

## 4. Files changed

Backend:
- `backend/apps/accounts/cookies.py` — **new** — cookie + CSRF helpers
- `backend/apps/accounts/services.py` — `_email_key`, invitation binding, `TeamService.set_user_status`
- `backend/apps/accounts/serializers.py` — status read-only, `MemberStatusSerializer`, dropped body-refresh serializers
- `backend/apps/accounts/views.py` — cookie auth flows, switch rotation + audit, `member_status_update_view`
- `backend/apps/accounts/urls.py` — status route
- `backend/config/settings/base.py` — refresh-cookie settings + `CONTENT_SECURITY_POLICY`
- `backend/config/settings/dev.py` — `CORS_ALLOW_CREDENTIALS`
- `backend/config/settings/prod.py` — secure cookie, credentials CORS, CSP connect-src, security middleware
- `backend/apps/core/middleware.py` — `SecurityHeadersMiddleware`

Frontend:
- `frontend/src/services/api.js` — cookie refresh + CSRF header, single-flight preserved, no refresh token in storage
- `frontend/src/pages/LoginPage.jsx`, `RegisterPage.jsx` — store access only
- `frontend/src/pages/DashboardPage.jsx` — logout sends CSRF header
- `frontend/src/components/Layout/TenantSwitcher.jsx` — access-only after switch
- `frontend/src/pages/TeamPage.jsx` — Enable/Disable actions

---

## 5. Migrations

None. No model changes were required (`config.settings` and behavior only). `py manage.py makemigrations --check --dry-run` → "No changes detected".

---

## 6. Tests added

New files (43 tests):
- `backend/apps/accounts/tests/test_invitation_binding.py` — 8
- `backend/apps/accounts/tests/test_refresh_cookie_csrf.py` — 10
- `backend/apps/accounts/tests/test_tenant_switch_session.py` — 12
- `backend/apps/accounts/tests/test_user_disable_api.py` — 11
- `backend/apps/core/tests/test_security_headers.py` — 2
- `backend/apps/accounts/tests/helpers.py` — shared cookie/CSRF/JWT helpers

Updated to the cookie flow: `test_auth_api.py` (register/login/refresh/rotation/logout) and `test_status_enforcement.py` (disabled-refresh now via cookie).

Coverage highlights: invitation forbids wrong email while staying reusable; refresh cookie attributes (HttpOnly/path/SameSite/max-age) and rotation; CSRF 403s; prod forces `SECURE`; switch binds and keeps tenant across rotations; old refresh cannot rewind; disabled users blocked everywhere; last-admin guard; `member.disable` audit; `me` cannot self-disable; CSP/security headers present.

---

## 7. Full regression result

```
$env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q
367 passed, 1 skipped in 21.16s
```

(The 1 skip is the pre-existing postgres-only test.)

## 8. Frontend build result

`npm run build` clean — vite 8.0.16, 130 modules, `dist/` 399.52 kB JS (110.36 kB gzip) / 1.78 kB CSS. Size delta vs baseline is within noise of the auth-flow change.

## 9. Frontend lint result

`npm run lint` — **16 problems (15 errors, 1 warning)**, byte-for-byte the pre-existing baseline (`react-hooks/set-state-in-effect` only). Zero new problems; ESLint no longer flags the removed `refresh` references. No auto-fix was applied (per constraint).

---

## 10. Contract changes

- `POST /auth/login`, `POST /auth/register` — `refresh` removed from the response body; a `Set-Cookie: refresh_token` (HttpOnly) and `csrftoken` cookie are written instead. `access`/`user`/`tenants`/`active_tenant` unchanged.
- `POST /auth/refresh` — reads the `refresh_token` cookie (no body); returns `{access}` only; requires `X-CSRFToken`.
- `POST /auth/logout` — revokes the cookie's refresh; requires `X-CSRFToken`; returns 205.
- `POST /tenants/switch/{id}` — response now also rotates the refresh cookie (still returns `access` + `tenant`; no `refresh` in body).
- `PATCH /auth/me/` — `status` is read-only (ignored input).
- New: `PATCH /tenants/members/{user_id}/status/` → `{status: "Active"|"Disabled"}`.
- All internal consumers (frontend pages, existing tests) were updated in the same change.

---

## 11. Constitution compliance changes

- No Feature 013 scope; the four objectives are hardening of the existing identity layer, not new product features.
- No deferred P2/P3 item was implemented implicitly: access-token revocation granularity, refresh `token_type` hardening, AUD-010/011/012/015/025/026/019/023/027/029 remain untouched and are documented in §13.
- Response contracts changed only where the hardening requires it and all internal consumers/tests were migrated in lockstep.
- Audit writes stay in the service layer (`AuditService.record`) — no view-layer audit logic for the two new actions (`tenant.switch`, `member.disable`/`member.enable`) beyond the record call in the view for the one pre-existing endpoint augmented.

---

## 12. Remaining P2/P3 items (not addressed — out of scope)

- **P2 open (6)**: AUD-010 (global request-handling redesign), AUD-011 (tenant_id on line tables), AUD-012 (Tenant PROTECT), AUD-015 (email delivery), AUD-025 (bcrypt hashing), AUD-026 (Celery + async mail/reports).
- **P3 open/partial (5+)**: AUD-019 (cardinal accounting error responses), AUD-023 (debug/perf scripts), AUD-027 (VITE env unfixed → compose `VITE_API_URL` uses `http://localhost:8000` without `/api/v1`), AUD-029 (pagination / N+1), plus the AUD-002 observations on access-token granularity and refresh `token_type` claim verification.
- These are target candidates for Feature 013 planning, not blockers for go-live given the READY WITH CONDITIONS verdict on 63 → 79 → now-clean-on-the-four-conditions trajectory.

---

## 13. Known limitations

- **Access token still lives in localStorage** (permitted residual): HttpOnly protection now covers the refresh token and the CSRF-bearing flows, but a successful XSS can still read the access token's 24 h session. Documented residual; full mitigation requires DESIGN-TOKEN-REDESIGN (access in memory/HttpOnly+credential flow) — out of scope.
- **CSRF**: enforced on the cookie-consuming endpoints (refresh/logout). Login is protected by SameSite=Lax + the fact it accepts only email/password (no ambient session); switch is protected by the Authorization header — a CSRF'd browser cannot forge an Authorization header. This is the documented single authoritative flow.
- **`CORS_ALLOW_ALL_ORIGINS` + `CORS_ALLOW_CREDENTIALS`** coexist in `dev.py` (reflects any origin) — a dev-only footgun accepted for DX, kept out of prod where origins are explicit.
- **Disable is global**: `status` on `User` is account-level; disabling in one tenant disables everywhere. Per-tenant removal is the existing `DELETE /tenants/members/{id}/`. This mirrors the data model and is documented on the endpoint.
- **No DB migration / no UI test harness**: all H2 changes are behavior+config; the frontend flow is covered by build + lint + manual verification checklists (no UI test framework exists).
- **`prod.py` CORS headers list** is additive on top of django-cors-headers defaults; `x-csrf-token`/`x-tenant-id` are explicitly allowed for credential-mode calls from the whitelisted origins.

---

## 14. Next steps (after review)

- Review this report and `specs/012-hardening-h2/*`; note the contract changes in §10 before any Feature 013 planning.
- Remaining P2/P3 (AUD-010, 011, 012, 015, 025, 026, 019, 023, 027, 029, plus access-token redesign) are documented for a future phase; AUD-025 (bcrypt) and AUD-026 (Celery) are the natural first candidates.
- Do not push or deploy; commit via the project's local-commit convention only.