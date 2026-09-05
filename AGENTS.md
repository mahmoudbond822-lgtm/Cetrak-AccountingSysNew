<!-- SPECKIT START -->
Implementation plan: specs/009-sales-cycle/plan.md

Current phase: IMPLEMENTATION COMPLETE — Feature 009 (Sales Cycle Foundation) implemented and all tests passing.

## What This Feature Does

Sales Cycle foundation — tenant-isolated Customers, Draft/Posted Sales Invoices with line-based decimal money math, and secure posting that generates a single balanced Journal Entry through an admin-configured (never hard-coded) per-tenant account mapping. Posting is idempotent and transactional; every invoice reference and account mapping is validated against the active tenant.

## Generated Artifacts

- `specs/009-sales-cycle/spec.md` — Feature specification
- `specs/009-sales-cycle/plan.md` — Implementation plan
- `specs/009-sales-cycle/research.md` — Technical research
- `specs/009-sales-cycle/data-model.md` — Data model
- `specs/009-sales-cycle/contracts/sales-api.md` — API contracts
- `specs/009-sales-cycle/quickstart.md` — Validation scenarios
- `specs/009-sales-cycle/tasks.md` — Implementation tasks
- `specs/009-sales-cycle/checklists/requirements.md` — Spec quality checklist

## Next Steps
- `/speckit.tasks` — Generate implementation tasks
- `/speckit.implement` — Execute the implementation

## Quick Reference
- Backend tests: `cd backend && py -m pytest apps/accounts/tests/ apps/accounting/tests/ apps/sales/tests/ -v`
- Test settings: DJANGO_SETTINGS_MODULE=config.settings.test
- Sales URLs: `api/v1/sales/customers/`, `api/v1/sales/invoices/`, `api/v1/sales/invoices/{id}/post_invoice/`, `api/v1/sales/settings/current/`
- Frontend: `npm run build` and `npm run lint` in `frontend/` (lint has pre-existing failures in earlier feature files; new sales files are clean)
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->