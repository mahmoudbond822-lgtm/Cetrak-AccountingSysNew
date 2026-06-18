# Implementation Plan: Accounting Frontend

**Branch**: `006-accounting-frontend` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-accounting-frontend/spec.md`

## Summary

Deliver the first usable accounting workflow — Chart of Accounts, Journal Entry creation/posting, Ledger view, and Financial Reports. This requires both:

1. **Backend additions**: Route the existing `JournalEntryViewSet`, add Ledger endpoint, add Report endpoints (Trial Balance, Income Statement, Balance Sheet) — the accounting backend is partially complete.
2. **Frontend implementation**: 6 new pages following existing patterns (React, inline styles, Axios, localStorage auth).

## Technical Context

**Language/Version**: Python 3.11+ (Django 5.2), JavaScript ES2022+ (React 19)

**Primary Dependencies**:
- Backend: Django REST Framework 3.15
- Frontend: React 19, React Router 7, Axios 1.17
- No additional packages needed — the stack is lean by design

**Storage**: PostgreSQL (backend), REST API calls (frontend — no local persistence)

**Testing**: pytest (backend), `cd backend && py -m pytest apps/accounting/tests/ -v`

**Target Platform**: Web — modern browsers (Chrome, Firefox, Edge, Safari)

**Project Type**: Web application (Django REST backend + React SPA frontend)

**Performance Goals**: Chart of Accounts loads in <3s; Journal Entry creation completes in <1 user-minute; Report generation in <5s

**Constraints**: JWT auth required on all requests; tenant isolation via `X-Tenant-ID` header; accounting integrity (debits = credits) enforced at frontend + API level; posted entries are immutable

**Scale/Scope**: 6 new pages, ~4 new backend endpoints, small-business SaaS (single-currency MVP)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Notes |
|-----------|-------|-------|
| **I. Multi-Tenancy** | ✅ PASS | All existing backend models are tenant-scoped via `TenantScopedModel`; frontend sends `X-Tenant-ID` automatically via Axios interceptor |
| **II. Accounting Integrity** | ✅ PASS | Journal entries enforce balance at model, serializer, and DB levels; posted entries are immutable (405 on PATCH/PUT/DELETE) |
| **III. API Rules** | ✅ PASS | All endpoints are RESTful, require auth via JWT interceptor, use consistent JSON |
| **IV. Code Standards** | ✅ PASS | Backend uses services layer (`AccountingService`, `JournalEntryService`); new Ledger/Report endpoints will follow same pattern |
| **V. AI Safety Rules** | ✅ N/A | No AI features in scope |
| **VI. Security** | ✅ PASS | JWT + tenant headers + role-based permissions (`HasAccountingAccess`) |
| **VII. Performance** | ✅ N/A | No heavyweight async tasks in scope |
| **VIII. MVP Discipline** | ✅ PASS | Scope limited to core accounting workflow; future enhancements explicitly deferred |

## Project Structure

### Documentation (this feature)

```text
specs/006-accounting-frontend/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — research findings
├── data-model.md        # Phase 1 — data model design
├── quickstart.md        # Phase 1 — validation guide
├── contracts/           # Phase 1 — API contracts
│   ├── accounts.md
│   ├── journal-entries.md
│   ├── ledger.md
│   └── reports.md
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── accounting/
│       ├── urls.py              # ADD JournalEntryViewSet routing
│       ├── views.py             # ADD LedgerViewSet, Report views
│       ├── services.py          # ADD LedgerService, ReportService
│       ├── serializers.py       # ADD Ledger/report serializers
│       └── permissions.py       # (unchanged — HasAccountingAccess)
│   └── accounts/
│       └── permissions.py       # ADD ManagerOrAccountant permission

frontend/
├── src/
│   ├── App.jsx                  # ADD accounting routes
│   ├── pages/
│   │   ├── ChartOfAccountsPage.jsx    # NEW
│   │   ├── CreateAccountPage.jsx      # NEW (or modal variant)
│   │   ├── JournalEntriesPage.jsx     # NEW
│   │   ├── JournalEntryFormPage.jsx   # NEW
│   │   ├── LedgerPage.jsx             # NEW
│   │   └── ReportsPage.jsx            # NEW
│   ├── components/
│   │   ├── accounting/
│   │   │   ├── AccountTree.jsx        # NEW
│   │   │   ├── AccountRow.jsx         # NEW
│   │   │   ├── JournalLineRow.jsx     # NEW
│   │   │   ├── AccountSelect.jsx      # NEW
│   │   │   ├── LedgerTable.jsx        # NEW
│   │   │   ├── ReportSelector.jsx     # NEW
│   │   │   └── ReportTable.jsx        # NEW
│   │   └── Layout/
│   │       ├── ProtectedRoute.jsx     # (existing)
│   │       └── AccountingNav.jsx      # NEW — nav sidebar/tabs
│   └── services/
│       └── api.js                     # (existing — no changes needed)
```

## Complexity Tracking

No constitution violations — all gates pass.

## Phase 0: Outline & Research

### Identified Unknowns

| # | Topic | Research Task |
|---|-------|--------------|
| U1 | Report aggregation queries | How to compute Trial Balance, Income Statement, Balance Sheet from JournalEntryLine data |
| U2 | Ledger running balance | How to compute running balance efficiently — Python-level vs DB-level |
| U3 | JournalEntryViewSet routing | Activate the existing dead-code viewset in urls.py |
| U4 | Permission for reports | Manager role needs report access (current `HasAccountingAccess` grants to Admin/Accountant only) |

### Research Dispatch

Research findings consolidated in [research.md](research.md).

## Phase 1: Design & Contracts

### Artifacts

1. **[data-model.md](data-model.md)** — No new models needed; all entities exist from 005-accounting-schema. Document frontend data structures.
2. **[contracts/](contracts/)** — API contracts for:
   - `accounts.md` — Account CRUD (existing, document for reference)
   - `journal-entries.md` — Journal Entry CRUD (needs routing activation)
   - `ledger.md` — Ledger query (new endpoint)
   - `reports.md` — Trial Balance, Income Statement, Balance Sheet (new endpoints)
3. **[quickstart.md](quickstart.md)** — Validation scenarios with setup commands
4. **Agent context** — Update `AGENTS.md` to reference this plan
