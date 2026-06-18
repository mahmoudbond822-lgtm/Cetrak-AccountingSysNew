# Research: Accounting UI Refactor

**Phase**: 0 — Technical Research & Clarification
**Date**: 2026-06-18
**Feature**: Accounting UI Refactor (007)

## Technology Stack

**Decision**: React 19 + Axios + React Router 7 — reuse existing stack.

**Rationale**: The existing frontend already uses React 19.2.6, axios 1.17, and react-router-dom 7.17. No new dependencies are needed for this refactoring. The project uses Vite 8.0 as the build tool with ESLint for code quality.

**Alternatives considered**:
- State management libraries (Redux, Zustand) rejected — existing codebase uses component-level state with Context API; adding a library would violate MVP Discipline
- Form libraries (React Hook Form, Formik) rejected — consistent with existing pattern of manual form state management
- CSS frameworks (Tailwind, Material UI) rejected — existing codebase uses inline styles with CSS variables

## Folder Structure

**Decision**: Domain-specific subdirectories under `components/accounting/`.

**Rationale**: Separating by domain (accounts, journal, ledger, reports) improves discoverability and follows established frontend patterns. Shared UI primitives go in `components/shared/`. Service layer goes in `services/`. Hooks go in `hooks/`.

**Alternatives considered**:
- Flat structure (current) — already proven to be less organized as component count grows
- Feature-sliced design — over-engineered for the current scope
- Pages-only — doesn't accommodate shared components between pages

## API Integration Pattern

**Decision**: Centralized `accountingService.js` class wrapping axios calls.

**Rationale**: The existing code has API calls scattered across page components. A centralized service provides a single source of truth for endpoint URLs, request/response shapes, and error handling. This follows the project's backend services layer pattern (Constitution IV) applied to the frontend.

**Pattern**:
- Service methods return raw axios promises
- Error handling is the caller's responsibility (consistent with existing patterns)
- No request/response transformation in the service layer — keep it thin

## State Management

**Decision**: Custom `useAccounting` hook for shared account state.

**Rationale**: The accounts list is needed across multiple pages (tree view, journal line dropdown, ledger selector). A custom hook provides shared state without adding a library. Other page-level state remains local to each page.

**Pattern**:
- Custom hooks for cross-cutting state
- Component-level `useState` / `useEffect` for page-local state
- No Context API or prop drilling for cross-page state — each page fetches what it needs

## Testing

**Decision**: No testing framework added.

**Rationale**: The existing project has no frontend test framework configured. Adding one is out of scope for this refactoring. Manual validation via the quickstart guide will be used instead.

**Future consideration**: If tests are added later, Vitest (compatible with Vite) would be the natural choice.

## Existing Code Audit

**Components to refactor** (from feature 006):

| Current File | New Location | Change |
|---|---|---|
| `components/accounting/AccountRow.jsx` | `components/accounting/accounts/AccountRow.jsx` | Move only |
| `components/accounting/AccountTree.jsx` | `components/accounting/accounts/AccountTree.jsx` | Move only |
| `components/accounting/AccountSelect.jsx` | `components/accounting/journal/AccountSelect.jsx` | Move only |
| `components/accounting/JournalLineRow.jsx` | `components/accounting/journal/JournalLineRow.jsx` | Move only |
| `components/accounting/LedgerTable.jsx` | `components/accounting/ledger/LedgerTable.jsx` | Move only |
| `components/accounting/ReportSelector.jsx` | `components/accounting/reports/ReportSelector.jsx` | Move only |
| `components/accounting/ReportTable.jsx` | `components/accounting/reports/ReportTable.jsx` | Move only |
| `pages/ChartOfAccountsPage.jsx` | `pages/accounting/AccountsPage.jsx` | Rename + extract CreateAccountModal |
| `pages/JournalEntryFormPage.jsx` | `pages/accounting/JournalPage.jsx` + `components/accounting/journal/JournalEntryForm.jsx` | Split page into page + extracted form |
| `pages/JournalEntriesPage.jsx` | Merged into `pages/accounting/JournalPage.jsx` | Merge list and form into single page |
| `pages/LedgerPage.jsx` | `pages/accounting/LedgerPage.jsx` | Move (unchanged) |
| `pages/ReportsPage.jsx` | `pages/accounting/ReportsPage.jsx` | Move (unchanged) |

**New files**:
| File | Purpose |
|---|---|
| `components/shared/Table.jsx` | Shared table component (used by LedgerTable, ReportTable) |
| `components/shared/Modal.jsx` | Shared modal component (used by AccountsPage for create/edit) |
| `components/shared/Button.jsx` | Shared button component (used by all pages) |
| `components/shared/Input.jsx` | Shared input component (used by journal form, account form) |
| `hooks/useAccounting.js` | Shared state hook for accounts list |
| `services/accountingService.js` | Centralized API service layer |
| `components/accounting/accounts/CreateAccountModal.jsx` | Extracted from ChartOfAccountsPage |

## Backend Dependencies

**No backend changes required**. All necessary endpoints already exist from feature 006:
- `GET/POST /api/v1/accounting/accounts/`
- `PATCH/DELETE /api/v1/accounting/accounts/{id}/`
- `GET /api/v1/accounting/accounts/?tree=true`
- `GET/POST /api/v1/accounting/journal-entries/`
- `POST /api/v1/accounting/journal-entries/{id}/post/`
- `GET /api/v1/accounting/ledger/?account_id={id}`
- `GET /api/v1/accounting/reports/trial-balance/`
- `GET /api/v1/accounting/reports/income-statement/`
- `GET /api/v1/accounting/reports/balance-sheet/`
