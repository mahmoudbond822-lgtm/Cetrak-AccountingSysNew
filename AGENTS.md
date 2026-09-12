<!-- SPECKIT START -->
Implementation plan: specs/012-hardening/plan.md

Current phase: HARDENING COMPLETE — Feature 012-H (Production Hardening) resolved all seven AUD-001 P1 blockers (07: unposted JEs in reports + Journal UI posting; balance-sheet net loss; refresh-token rotation; invoice modal reset; Decimal money math; immutable audit trail; disabled-user/suspended-tenant enforcement). Features 001–012 remain implemented. Full suite 324 passed, 1 postgres-only skip, migrations clean, frontend build green, lint unchanged (16 pre-existing problems). Do not push or deploy.

## What This Phase Does

Closes the P1 blockers from `docs/audits/production-readiness-audit-001.md` (READY WITH CONDITIONS, 63/100) without creating Feature 013:
- **P1-1** Ledger + all report aggregation filter `entry__posted=True`; Journal UI has a real Save Draft → Post flow.
- **P1-2** Balance Sheet no longer clamps; net loss flows signed into "Retained Earnings (Current Period)" and the sheet balances in loss periods.
- **P1-3** Frontend refresh interceptor is single-flight, persists the rotated refresh token, retries the original request, clears the session only on genuine failure.
- **P1-4** Invoice modal remounts per record (`key`-remount, parity with payment/purchase pages).
- **P1-5** Accounting service + serializer money math is Decimal with exact equality (float tolerance removed).
- **P1-6** New append-only `core.AuditLog` + `AuditService` writes tenant/actor-scoped, immutable, sanitized audit rows from every service-layer mutation.
- **P1-7** Shared `TenantScopedPermission` base enforces ACTIVE user + ACTIVE tenant + membership on every endpoint; JWT auth rejects disabled users; `/tenants/switch/` refuses non-ACTIVE tenants.

## Generated Artifacts

- `docs/audits/production-hardening-report-001.md` — Authoritative hardening report (baseline, findings, files, tests, regression, readiness)
- `specs/012-hardening/spec.md` — Hardening specification (implemented)
- `specs/012-hardening/plan.md` — Implementation plan, phases H1–H7 (implemented)
- `specs/012-hardening/tasks.md` — Implementation tasks (all complete)
- `specs/012-hardening/data-model.md` — `core_audit_log` data model + immutability notes
- `specs/012-hardening/quickstart.md` — Manual verification (P1-3/P1-4 frontend; no UI test harness)
- `specs/012-hardening/checklists/requirements.md` — Spec quality checklist (verified at close-out)
- `specs/012-hardening/report.md` — Implementation report

## Key Decisions (locked in the plan)

- Report/ledger inclusion requires `posted=True` unconditionally (no permission-gated draft inclusion this pass).
- Audit writes happen exclusively in the service layer via `AuditService.record`; no view-layer audit logic; sensitive keys recursively scrubbed (password/refresh/access/token/secret/api_key/session).
- Status enforcement centralized: `TenantScopedPermission` (core) is the single membership + ACTIVE-tenant gate; `BlacklistCheckingJWTAuth` rejects non-ACTIVE users on valid tokens (no reliance on token expiry).
- No token-storage redesign (HttpOnly cookies deferred to AUD-009/P2); no DB-level audit trigger (app-layer guards + no write endpoints; documented limitation).
- Backend half of P1-1/P1-2/P1-5 + Journal UI posting landed in commit `ec5563a` (18 integrity tests); this pass delivered P1-3/P1-4/P1-6/P1-7 and verified all seven end-to-end.

## Next Steps (after review)

- Review the hardening report and `specs/012-hardening/*`. Remaining P2/P3 items (AUD-008…AUD-030, e.g. bcrypt, Celery, HttpOnly tokens, pagination) are out of scope and documented for future phases. Do not push or deploy; commit via the auto-commit hook only.

## Quick Reference

- Backend tests: `cd backend && $env:DJANGO_SETTINGS_MODULE="config.settings.test"; py -m pytest apps/ -q` → 324 passed, 1 postgres-only skip (274 baseline + 18 financial-integrity + 4 token-rotation + 10 status-enforcement + 17 audit-trail + 52-inventory + 223 pre-existing)
- New backend pieces: `apps/core/audit.py`, `apps/core/permissions.py`, `core.AuditLog` (migration `core/0002_auditlog`), `AuditService.record(...)` wired into accounts/accounting/sales/purchases/inventory services
- Frontend changed files: `src/services/api.js` (single-flight rotated refresh), `src/pages/sales/InvoicesPage.jsx` (modal remount `key`)
- Migrations: `py manage.py makemigrations --check --dry-run` → "No changes detected"
- Frontend: `npm run build` clean; `npm run lint` still exactly 16 pre-existing problems (zero new)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->