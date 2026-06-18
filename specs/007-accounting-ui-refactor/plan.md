# Implementation Plan: Accounting UI Refactor

**Branch**: `007-accounting-ui-refactor` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-accounting-ui-refactor/spec.md`

## Summary

Refactor the existing accounting frontend (built in feature 006) into a clean component architecture with domain-specific subdirectories (`accounts/`, `journal/`, `ledger/`, `reports/`), a centralized API service layer (`accountingService.js`), a shared state hook (`useAccounting.js`), and reusable UI components (`Table`, `Modal`, `Button`, `Input`). The goal is improved maintainability, code reuse, and consistent user experience across all accounting pages.

## Technical Context

**Language/Version**: JavaScript (React 19.2.6)

**Primary Dependencies**: react-router-dom (7.17), axios (1.17), vite (8.0)

**Storage**: N/A — frontend only; all data persisted via REST API to Django backend

**Testing**: No test framework configured (ESLint only for linting). Existing project does not use Jest/Vitest.

**Target Platform**: Modern web browsers (Chrome, Firefox, Edge)

**Project Type**: Single-page application frontend (Vite + React)

**Performance Goals**: Pages render within 2 seconds (SC-001); journal form detects imbalance within 200ms (SC-003)

**Constraints**: Must reuse existing patterns (inline styles with CSS variables, axios with JWT/tenant headers). No state management library or form library — consistent with existing codebase conventions.

**Scale/Scope**: ~4 pages, ~10 components, single developer iteration on existing codebase

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Tenancy** | ✅ Pass | Frontend-only refactor; existing tenant header middleware unchanged |
| **II. Accounting Integrity** | ✅ Pass | Frontend enforces balance validation before submit; no changes to immutable entry rules |
| **III. API Rules** | ✅ Pass | Using existing RESTful backend; `accountingService.js` wraps existing endpoints |
| **IV. Code Standards** | ✅ Pass | Services layer pattern respected — accountingService is the frontend service layer. No business logic in components. |
| **V. AI Safety Rules** | ✅ Pass | AI-generated code changes require user confirmation before application |
| **VI. Security** | ✅ Pass | Reusing existing JWT auth and tenant isolation; no new security surface |
| **VII. Performance** | ✅ Pass | No heavyweight tasks added; all UI operations are synchronous, client-side only |
| **VIII. MVP Discipline** | ✅ Pass | Refactor of existing code only — no scope expansion |

## Project Structure

### Documentation (this feature)

```text
specs/007-accounting-ui-refactor/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

**Structure Decision**: Web application (frontend only refactor — backend untouched).

```text
frontend/src/
├── components/
│   └── accounting/
│       ├── accounts/
│       │   ├── AccountRow.jsx        # Recursive tree row (moved from accounting/)
│       │   ├── AccountTree.jsx       # Tree container (moved from accounting/)
│       │   └── CreateAccountModal.jsx # New: extracted modal from ChartOfAccountsPage
│       ├── journal/
│       │   ├── AccountSelect.jsx     # Searchable dropdown (moved from accounting/)
│       │   ├── JournalLineRow.jsx    # Debit/credit line (moved from accounting/)
│       │   └── JournalEntryForm.jsx  # New: extracted form from JournalEntryFormPage
│       ├── ledger/
│       │   └── LedgerTable.jsx       # Running balance table (moved from accounting/)
│       └── reports/
│           ├── ReportSelector.jsx    # Type/date range selector (moved from accounting/)
│           └── ReportTable.jsx       # Report renderer (moved from accounting/)
├── components/shared/
│   ├── Table.jsx                     # New: shared table component
│   ├── Modal.jsx                     # New: shared modal component
│   ├── Button.jsx                    # New: shared button component
│   └── Input.jsx                     # New: shared input component
├── hooks/
│   └── useAccounting.js              # New: shared state hook
├── pages/
│   └── accounting/
│       ├── AccountsPage.jsx          # Renamed from ChartOfAccountsPage
│       ├── JournalPage.jsx           # Renamed from JournalEntriesPage (includes form)
│       ├── LedgerPage.jsx            # Moved from pages/ (unchanged)
│       └── ReportsPage.jsx           # Moved from pages/ (unchanged)
├── services/
│   └── accountingService.js          # New: centralized API service
├── App.jsx                           # Update routes to new page paths
└── components/Layout/
    └── AccountingNav.jsx             # Unchanged
```

## Complexity Tracking

> All Constitution Check gates passed — no complexity tracking needed.
