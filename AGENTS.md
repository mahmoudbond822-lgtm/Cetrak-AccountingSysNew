<!-- SPECKIT START -->
Implementation plan: specs/007-accounting-ui-refactor/plan.md

Current phase: IMPLEMENTATION COMPLETE — Feature 007 (Accounting UI Refactor) fully implemented across 6 phases (25 tasks).

## Completed Work

### Phase 1 — Setup (Shared Infrastructure)
- Created directory structure: `components/accounting/{accounts,journal,ledger,reports}/`, `components/shared/`, `hooks/`, `services/`, `pages/accounting/`
- Shared components: `Button.jsx`, `Input.jsx`, `Modal.jsx`, `Table.jsx`
- Service layer: `services/accountingService.js` (thin wrapper over axios)
- Shared hook: `hooks/useAccounting.js`

### Phase 2 — US1: Chart of Accounts
- Moved `AccountRow.jsx`, `AccountTree.jsx` → `accounts/` subdirectory
- Extracted `CreateAccountModal.jsx` from old page
- Created `AccountsPage.jsx` at `pages/accounting/`

### Phase 3 — US2: Journal Entry
- Moved `AccountSelect.jsx`, `JournalLineRow.jsx` → `journal/` subdirectory
- Extracted `JournalEntryForm.jsx` (standalone form component)
- Created `JournalPage.jsx` at `pages/accounting/` (list + inline form)

### Phase 4 — US3: Ledger View
- Moved `LedgerTable.jsx` → `ledger/` subdirectory
- Created `LedgerPage.jsx` at `pages/accounting/`

### Phase 5 — US4: Financial Reports
- Moved `ReportSelector.jsx`, `ReportTable.jsx` → `reports/` subdirectory
- Created `ReportsPage.jsx` at `pages/accounting/`

### Phase 6 — Polish & Routes
- Updated `App.jsx` routes to use new page paths
- Removed all old page files (ChartOfAccountsPage, JournalEntriesPage, JournalEntryFormPage, LedgerPage, ReportsPage)
- Fixed pre-existing syntax error in `AccountingNav.jsx`
- Removed dead `/accounting/journal/new` NavLink (form now inline)
- `npx vite build` passes (clean compile, 322 KB gzipped)

## Next Steps
- Run quickstart.md validation scenarios (manual, requires running backend + frontend)

## Generated Artifacts

- `specs/007-accounting-ui-refactor/spec.md` — Feature specification
- `specs/007-accounting-ui-refactor/plan.md` — Implementation plan
- `specs/007-accounting-ui-refactor/research.md` — Technical research & audit
- `specs/007-accounting-ui-refactor/data-model.md` — Frontend data shapes
- `specs/007-accounting-ui-refactor/contracts/api.md` — Service layer API contracts
- `specs/007-accounting-ui-refactor/quickstart.md` — Validation scenarios
- `specs/007-accounting-ui-refactor/checklists/requirements.md` — Spec quality checklist

## What This Feature Does

Refactor the existing accounting frontend (feature 006) into a clean component architecture:
- Domain-specific subdirectories: `accounts/`, `journal/`, `ledger/`, `reports/`
- Centralized API service layer: `services/accountingService.js`
- Shared state hook: `hooks/useAccounting.js`
- Reusable UI components: `components/shared/{Table,Modal,Button,Input}.jsx`
- Pages reorganized under `pages/accounting/`

## Key Decisions
- No new dependencies — reuse existing React 19 + Axios + React Router 7
- No test framework — consistent with existing project setup
- Service layer mirrors backend's services pattern (thin wrapper over axios)
- Shared components extracted from existing page-specific implementations

## Next Steps
- `/speckit.tasks` — Generate implementation tasks
- `/speckit.implement` — Execute the refactoring

## Quick Reference
- Frontend build: `cd frontend && npx vite build`
- Backend tests: `cd backend && py -m pytest apps/accounts/tests/ -v`
- Accounting tests: `cd backend && py -m pytest apps/accounting/tests/ -v`
- Test settings: DJANGO_SETTINGS_MODULE=config.settings.test
- Docker Compose: `docker compose -f infra/docker-compose.yml up`
<!-- SPECKIT END -->
