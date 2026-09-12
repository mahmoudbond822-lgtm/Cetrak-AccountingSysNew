# Spec Quality Checklist: 012-H2 Identity & Session Hardening

Verified at close-out against `.specify/memory/constitution.md` and AUD-002 (AUD-008, AUD-009, AUD-017 + user-disable gap).

## Requirement completeness

- [x] H2-1 invitations stored with canonical email key (`_email_key` = strip + lower) — tested.
- [x] H2-1 invitation acceptance bound to the invited email only; case/whitespace variants match — tested.
- [x] H2-1 mismatch rejected before user creation; invitation remains reusable; no email leakage — tested.
- [x] H2-2 refresh token absent from all response bodies (login/register/refresh) — tested.
- [x] H2-2 refresh cookie HttpOnly, path `/api/v1/`, SameSite=Lax, max-age aligned to 7d/30d remember-me — tested.
- [x] H2-2 refresh secure in prod (`REFRESH_COOKIE_SECURE=True` + kwargs-level prod test) — tested.
- [x] H2-2 CSRF double-submit on refresh/logout; missing/wrong header → 403; constant-time compare — tested.
- [x] H2-2 CSP + nosniff + Referrer-Policy + Permissions-Policy only in prod (`SecurityHeadersMiddleware`) — tested.
- [x] H2-2 frontend single-flight refresh preserved; cookie read via browser; no refresh token in storage — build + lint + code inspection.
- [x] H2-3 switch rotates the refresh cookie scoped to the target tenant — tested.
- [x] H2-3 refresh after switch preserves tenant context; old pre-switch refresh cannot rewind — tested.
- [x] H2-3 `tenant.switch` audited with source (from access-token claim) + target — tested.
- [x] H2-4 `PATCH /tenants/members/{id}/status/` admin-only, tenant-scoped 404, last-admin guard — tested.
- [x] H2-4 disabled users blocked at login / on-request / on-refresh / on-switch; re-enable restores — tested.
- [x] H2-4 `me` PATCH cannot change `status` (read-only) — tested.
- [x] H2-4 `member.disable`/`member.enable` audited — tested.

## Regression gates

- [x] Full backend suite: **367 passed, 1 skipped** (≥ 324 baseline preserved, +43 new).
- [x] `py manage.py makemigrations --check --dry-run` → "No changes detected".
- [x] `npm run build` — pass (399.52 kB JS / 110.36 kB gzip).
- [x] `npm run lint` — 16 problems, identical to pre-existing baseline; zero new.
- [x] Existing auth/team/status/two-step suites still green under the cookie contract (helpers migrated).

## Governance / scope

- [x] No Feature 013 created; no product scope added.
- [x] No deferred P2/P3 implemented (AUD-010/011/012/015/025/026/019/023/027/029 + access-token redesign untouched).
- [x] No push / no deploy (per AGENTS.md constraint).
- [x] Changes restricted to H2-1…H2-4 scope; working-tree diff inspected before commit.
- [x] Constitution impact documented in `report.md` and the hardening report (§11).