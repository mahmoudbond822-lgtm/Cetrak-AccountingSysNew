# Implementation Plan: Auto Customer Code

**Branch**: `014-auto-customer-code` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-auto-customer-code/spec.md`

## Summary

Creating a customer currently fails with `{"code":["This field is required."]}`. This plan makes the system own the code: the backend mints the next per-business code (`CUS-0001`, +1 per saved customer) at save time, and the create dialog shows that next code in a visible but disabled (non-editable) field. Preview is a hint only — the authoritative assignment happens at save, skipping collisions, scoped per business, immutable on edit. No schema migration; behavior + presentation only.

## Technical Context

**Language/Version**: Python 3.14 backend (Django + DRF); React frontend (existing toolchain, npm)

**Primary Dependencies**: Django, Django REST Framework (backend); React (frontend)

**Storage**: SQLite for dev/test (`config.settings.test`); Postgres via Docker Compose for prod-like env. No schema change — `Customer.code` CharField(50) with existing per-tenant unique constraint is reused as-is.

**Testing**: `py -m pytest apps/ -q` with `DJANGO_SETTINGS_MODULE=config.settings.test` (backend, currently 375 passed / 1 skipped); `npm run build` + `npm run lint` (frontend)

**Target Platform**: Web application — Django API (`backend/`) + React SPA (`frontend/`), served via Docker Compose

**Project Type**: Web application (backend + frontend)

**Performance Goals**: No new target — mint is one extra indexed lookup (max numeric suffix among the tenant's customer codes) per customer create; negligible vs. request cost

**Constraints**: Behavior-only change (no migration; `makemigrations --check` must stay clean); tenant isolation must hold on every query; no push/deploy (commit via hook only)

**Scale/Scope**: One dialog (`CustomerModal`), one service path (`CustomerService.create` / `create_with_flag`), one serializer path (`CustomerSerializer`); per-business sequential codes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Multi-Tenancy (non-negotiable) | PASS | Mint reads max suffix scoped to `request.tenant_id` only; uniqueness enforced per tenant by existing constraint |
| II. Accounting Integrity | PASS | No journal/ledger touch; codes immutable on edit, never blanked or regenerated |
| III. API Rules | PASS | RESTful POST/PATCH; auth required; consistent JSON; 201 on create, 200 on idempotent same-tenant duplicate |
| IV. Code Standards (services layer) | PASS | Mint lives in `CustomerService` (`create` / `create_with_flag` + next-code helper); views stay thin |
| V. AI Safety | N/A | No AI surface in this feature |
| VI. Security | PASS | Tenant isolation enforced at service + middleware layers; no cross-tenant sequence leak |
| VII. Performance | PASS | Single indexed max-suffix scan per create; no async work needed |
| VIII. MVP Discipline | PASS | Scoped to customer create dialog + mint path; vendors/invoices numbering untouched |

Post-design re-check: no new components, no schema change, no new endpoints — all gates still PASS. Nothing to justify in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-auto-customer-code/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── customer-create.md
├── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── apps/sales/
│   ├── models.py        # Customer (unchanged schema)
│   ├── serializers.py   # CustomerSerializer: code optional/allow_blank, blank → mint
│   ├── services.py      # CustomerService.create / create_with_flag + next-code helper
│   ├── views.py         # Customer create: tuple unpack, 201 created / 200 existing
│   └── tests/
│       ├── test_auto_customer_code.py
│       └── test_customer_api_create_without_code.py

frontend/
├── src/
│   ├── components/sales/customers/
│   │   └── CustomerModal.jsx   # Create mode: disabled Code preview of next code
│   └── services/
│       └── salesService.js     # create payload omits code
```

**Structure Decision**: Web application layout (Option 2). Backend mint + serializer paths already landed and green; remaining work is the create-dialog disabled preview plus the save-time authoritative assignment note. No new apps, no migrations.

## Complexity Tracking

No constitution violations — table intentionally empty.
