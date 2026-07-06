# Implementation Plan: P0 Tenant Isolation

**Branch**: `main` | **Date**: 2026-07-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-p0-tenant-isolation/spec.md`

## Summary

Close the P0 tenant isolation gap in accounting write paths by ensuring all account references used for account hierarchy and journal entry creation belong to the active tenant. The implementation will keep the current backend architecture, add targeted validation at the accounting boundary, and add regression tests proving cross-tenant parent accounts, cross-tenant journal lines, and mixed-tenant entries are rejected without partial writes or data disclosure.

## Technical Context

**Language/Version**: Python 3.x backend, Django 5.0.x, JavaScript/React frontend present but not in scope for this backend isolation fix

**Primary Dependencies**: Django, Django REST Framework, Simple JWT, pytest/Django test runner, PostgreSQL in production configuration

**Storage**: PostgreSQL for production; test database configured through Django test settings

**Testing**: Existing backend API tests under `backend/apps/accounting/tests/` and `backend/apps/accounts/tests/`

**Target Platform**: Web service backend deployed behind the existing API and tenant middleware

**Project Type**: Multi-tenant web application with backend API and frontend client

**Performance Goals**: Tenant validation must add no noticeable delay to normal account and journal entry submission

**Constraints**: No new dependencies; no schema migration expected; preserve existing same-tenant accounting behavior; rejected operations must not create partial accounting records

**Scale/Scope**: Narrow P0 production-readiness fix for accounting account hierarchy and journal entry write paths, plus regression coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Multi-Tenancy (NON-NEGOTIABLE)**: PASS. The feature exists to enforce active-tenant filtering on accounting write references.
- **Accounting Integrity (CRITICAL)**: PASS. Mixed-tenant entries must be rejected entirely, preventing corrupted ledgers and reports.
- **API Rules**: PASS. Existing authenticated API boundaries remain unchanged; validation errors stay consistent with current API behavior.
- **Code Standards**: PASS. The implementation will stay in the existing serializer/service/test structure and avoid new architectural layers.
- **AI Safety Rules**: PASS. No AI behavior is introduced.
- **Security**: PASS. Tenant isolation is strengthened for write paths and safe errors must not disclose other tenants' data.
- **Performance**: PASS. Scope is small reference validation using existing data access patterns; no heavyweight async work is introduced.
- **MVP Discipline**: PASS. Scope is limited to the confirmed P0 blocker and excludes backup/DR, AI, billing, deployment, and broader accounting correctness refactors.

Post-design re-check: PASS. Phase 1 artifacts keep the same scope, require no new dependency, and preserve the constitution constraints above.

## Project Structure

### Documentation (this feature)

```text
specs/008-p0-tenant-isolation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── accounting-api.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── accounting/
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   └── tests/
│   │       └── test_accounting_api.py
│   ├── accounts/
│   │   ├── models.py
│   │   └── tests/
│   └── core/
│       └── middleware.py
└── config/
    └── settings/
        └── test.py
```

**Structure Decision**: Use the existing backend accounting module. The primary implementation surface is `backend/apps/accounting/serializers.py`, with possible service-level hardening if needed to guarantee no partial writes. Regression coverage belongs in `backend/apps/accounting/tests/test_accounting_api.py` alongside the existing multi-tenant accounting tests.

## Complexity Tracking

No constitution violations or added complexity are required for this feature.
