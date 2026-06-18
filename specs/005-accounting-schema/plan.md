# Implementation Plan: Accounting Schema

**Branch**: `005-accounting-schema` | **Date**: 2026-06-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-accounting-schema/spec.md`

## Summary

Build the core double-entry accounting schema: a hierarchical Chart of Accounts (Asset, Liability, Equity, Revenue, Expense) and a Journal Entry system with header+lines that enforces the constitutional hard rule — no entry is persisted unless total debits equal total credits. This phase is strictly schema + data integrity; financial reports, fiscal periods, opening balances, and multi-currency are deferred.

## Technical Context

**Language/Version**: Python 3.14 (from project convention), Django 6.0.4

**Primary Dependencies**: Django REST Framework, psycopg2-binary (PostgreSQL adapter); django-mptt or django-treebeard (tree structure for Chart of Accounts)

**Storage**: PostgreSQL 15+ (production), SQLite :memory: (tests)

**Testing**: pytest 9.x + pytest-django, DRF APITestCase; 36 existing tests must continue to pass

**Target Platform**: Linux Docker containers, modern web browsers (Chrome, Firefox, Edge)

**Project Type**: web-service (Django backend + React frontend)

**Performance Goals**: Chart of Accounts tree render <2s at 500 accounts (SC-003); journal entry creation <3s round-trip (SC-001)

**Constraints**: Constitution Article II (Accounting Integrity) requires the balanced-entry enforcement at the data layer; existing multi-tenancy (Article I) applies to all new models

**Scale/Scope**: 50 users/tenant MVP, single-region deployment; the `apps/accounting/` directory already exists as a placeholder

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Principle | Status | Notes |
|---------|-----------|--------|-------|
| I | Multi-Tenancy | ✅ Compliant | All accounts and journal entries are tenant-scoped via `TenantScopedModel` |
| II | Accounting Integrity | ✅ Compliant | Balanced-entry rule enforced at both application and data layer (FR-006) |
| III | API Rules | ✅ Compliant | Endpoints follow existing DRF patterns (views, serializers, permissions) |
| IV | Code Standards | ✅ Compliant | Business logic in services layer; models in `apps/accounting/` |
| V | AI Safety Rules | ✅ Not Applicable | No AI-generated content in this feature |
| VI | Security | ✅ Compliant | Existing multi-tenancy middleware protects accounting data |
| VII | Performance | ✅ Compliant | Tree render target <2s at 500 accounts; journal entry creation <3s |
| VIII | MVP Discipline | ✅ Compliant | Reports, periods, opening balances, multi-currency explicitly deferred |

**No violations found.** Constitution gates passed.

## Project Structure

### Documentation (this feature)

```text
specs/005-accounting-schema/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── accounting/                  # NEW: populated from placeholder
│   │   ├── __init__.py
│   │   ├── models.py                # Account (hierarchical, typed) + JournalEntry + JournalEntryLine
│   │   ├── serializers.py           # DRF serializers for all models
│   │   ├── views.py                 # CRUD endpoints (create/list accounts, create/list journal entries)
│   │   ├── services.py              # Business logic: create_account, create_journal_entry, validate_balanced
│   │   ├── permissions.py           # Accounting-specific permissions (accountant role)
│   │   ├── urls.py                  # Route registration
│   │   ├── migrations/              # Initial migration for accounting models
│   │   └── tests/                   # Feature-specific tests
│   │       ├── test_accounts.py
│   │       ├── test_journal_entries.py
│   │       └── test_balanced_entry_rule.py
│   └── core/
│       └── models.py                # TenantScopedModel (already exists, used by accounting)
├── config/
│   └── settings/
│       └── base.py                  # apps.accounting already in INSTALLED_APPS (no change)
└── specs/
    └── 005-accounting-schema/       # This feature's documentation
```

**Structure Decision**: All new code goes into the existing `apps/accounting/` directory (currently a placeholder with only `__init__.py`). No structural changes needed outside this app.

## Complexity Tracking

No constitutional violations to justify.

## Phase 0: Research

Two unknowns need investigation before design:

1. **Tree library choice**: django-mptt vs django-treebeard vs materialized-path via recursion for the Chart of Accounts hierarchy. Evaluate against Django 6.0.4 compatibility, PostgreSQL WITH RECURSIVE support, and simplicity.
2. **Balanced-entry enforcement strategy**: Django model-level validation (`clean()`) vs database-level constraint (CHECK constraint or trigger) vs a combination. Evaluate per FR-006 (enforced at both layers).

Key findings consolidated in [research.md](./research.md).

## Phase 1: Design

### Data Model

Three new entities: Account, JournalEntry, JournalEntryLine. See [data-model.md](./data-model.md) for full details.

| Entity | Key Fields | Relationships |
|--------|-----------|---------------|
| Account | name, type (enum), parent (self-FK nullable) | TenantScopedModel, tree structure |
| JournalEntry | date, description, reference | TenantScopedModel, 1:N with lines |
| JournalEntryLine | account (FK), debit amount, credit amount | FK to JournalEntry, FK to Account |

### API Contracts

Standard RESTful CRUD endpoints under `/api/v1/accounting/`. See [contracts/](./contracts/) for full request/response schemas.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/accounting/accounts/` | GET/POST | List (tree) / Create accounts |
| `/api/v1/accounting/accounts/:id/` | GET | Account detail |
| `/api/v1/accounting/journal-entries/` | GET/POST | List / Create journal entries |
| `/api/v1/accounting/journal-entries/:id/` | GET | Entry detail with lines |

### Quickstart Validation

Validation guide in [quickstart.md](./quickstart.md) — 5 runnable scenarios covering account tree creation, balanced entry creation, unbalanced entry rejection, immutability, and tenant isolation.
