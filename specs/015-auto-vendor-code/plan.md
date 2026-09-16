# Implementation Plan: Auto Vendor Code

**Branch**: `015-auto-vendor-code` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-auto-vendor-code/spec.md`

## Summary

Creating a vendor currently fails with `{"code":["Vendor code is required."]}` when no code is typed. This plan mirrors Feature 014 (auto customer code): the backend mints the next per-business code (`VEN-0001`, +1 per saved vendor) at save time, and the create dialog shows that next code in a visible but disabled (non-editable) field. Preview is a hint only — authoritative assignment happens at save, skipping collisions, scoped per business, immutable on edit. No schema migration; behavior + presentation only. One structural difference from 014: vendor creation logic currently lives in the view (`VendorViewSet.create` calls `get_or_create` inline), so a `VendorService` is introduced in `apps/purchases/services.py` per constitution principle IV (no fat views).

## Technical Context

**Language/Version**: Python 3.14 backend (Django + DRF); React frontend (existing toolchain, npm)

**Primary Dependencies**: Django, Django REST Framework (backend); React (frontend)

**Storage**: SQLite for dev/test (`config.settings.test`); Postgres via Docker Compose for prod-like env. No schema change — `Vendor.code` CharField(50) with existing `unique_vendor_code_per_tenant` constraint is reused as-is.

**Testing**: `py -m pytest apps/ -q` with `DJANGO_SETTINGS_MODULE=config.settings.test` (backend, currently 375 passed / 1 skipped); `npm run build` + `npm run lint` (frontend, 18 pre-existing lint problems)

**Target Platform**: Web application — Django API (`backend/`) + React SPA (`frontend/`), served via Docker Compose

**Project Type**: Web application (backend + frontend)

**Performance Goals**: No new target — mint is one extra indexed lookup (max numeric suffix among the tenant's vendor codes) per vendor create; negligible vs. request cost

**Constraints**: Behavior-only change (no migration; `makemigrations --check` must stay clean); tenant isolation must hold on every query; no push/deploy (commit via hook only)

**Scale/Scope**: One dialog (`VendorModal`), one page (`VendorsPage` preview helper + assigned-code notice), one service path (new `VendorService.create_with_flag`), one serializer path (`VendorSerializer`); per-business sequential codes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Multi-Tenancy (non-negotiable) | PASS | Mint reads max suffix scoped to `request.tenant_id` only; uniqueness enforced per tenant by existing constraint |
| II. Accounting Integrity | PASS | No journal/ledger touch; codes immutable on edit, never blanked or regenerated |
| III. API Rules | PASS | RESTful POST/PATCH; auth required; consistent JSON; 201 on create, 200 on idempotent same-tenant duplicate |
| IV. Code Standards (services layer) | PASS | Mint lives in new `VendorService` (`create_with_flag` + next-code helper); `VendorViewSet.create` thinned to call it |
| V. AI Safety | N/A | No AI surface in this feature |
| VI. Security | PASS | Tenant isolation enforced at service + middleware layers; no cross-tenant sequence leak |
| VII. Performance | PASS | Single indexed max-suffix scan per create; no async work needed |
| VIII. MVP Discipline | PASS | Scoped to vendor create dialog + mint path; customer/invoice numbering untouched |

Post-design re-check: no new components beyond one service class, no schema change, no new endpoints — all gates still PASS. Nothing to justify in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/015-auto-vendor-code/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── vendor-create.md
├── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── apps/purchases/
│   ├── models.py        # Vendor (unchanged schema)
│   ├── serializers.py   # VendorSerializer: code optional/allow_blank, blank → mint
│   ├── services.py      # NEW VendorService.create_with_flag + next-code helper
│   ├── views.py         # Vendor create: delegate to VendorService, 201 created / 200 existing
│   └── tests/
│       ├── test_vendors_api.py        # existing (test_create_vendor_requires_code_and_name still passes: name still required)
│       └── test_auto_vendor_code.py   # NEW: mint sequence, prefix, blank-mint, edit-preserves, cross-tenant

frontend/
├── src/
│   ├── components/purchases/vendors/
│   │   └── VendorModal.jsx     # Create mode: disabled Code preview of next code; payload omits code
│   ├── pages/purchases/
│   │   └── VendorsPage.jsx     # next-code preview helper + assigned-code notice on stale preview
│   └── services/
│       └── purchasesService.js # unchanged (payload already passes data through)
```

**Structure Decision**: Web application layout (Option 2). Mirrors the proven 014 shape exactly, plus one service-class introduction to satisfy the services-layer rule that the customer side already met.

## Complexity Tracking

No constitution violations — table intentionally empty.
