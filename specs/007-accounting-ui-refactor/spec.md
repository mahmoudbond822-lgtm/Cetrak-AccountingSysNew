# Feature Specification: Accounting UI Refactor

**Feature Branch**: `007-accounting-ui-refactor`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Accounting Frontend — Component Architecture specification covering Chart of Accounts, Journal Entry, Ledger, Reports at the component, state, and API integration level"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Standardized Page & Component Structure (Priority: P1)

As an accountant, I want to navigate accounting pages that have a consistent layout and behavior so that I can predictably perform my daily work without confusion.

**Why this priority**: Consistent UI is foundational to user trust and efficiency. Every subsequent feature depends on this structure.

**Independent Test**: Navigate between Accounts, Journal, Ledger, and Reports pages. Verify each page has the same header layout, navigation, loading states, and error handling patterns.

**Acceptance Scenarios**:

1. **Given** I am on any accounting page, **When** I look at the layout, **Then** it uses the standard page template with consistent header, content area, and footer
2. **Given** I am in the accounting section, **When** I navigate between pages, **Then** the transition is smooth and each page maintains the same chrome/navigation
3. **Given** a page is loading data, **When** the API call is in progress, **Then** I see a loading indicator in the content area

---

### User Story 2 - Centralized API Service & State Management (Priority: P1)

As a developer maintaining the accounting module, I want all API calls routed through a single service layer and reusable state hooks so that endpoint URLs and data fetching logic are maintained in one place.

**Why this priority**: Reduces code duplication, makes API changes safer, and provides a single source of truth for data operations.

**Independent Test**: All accounting pages fetch data through `accountingService.js`. Verify that mocking this service in tests replaces all API interactions.

**Acceptance Scenarios**:

1. **Given** the accounting module, **When** any page needs to fetch or mutate data, **Then** it uses a method from `accountingService.js`
2. **Given** the accounting module, **When** a component needs shared state (accounts list, loading, error), **Then** it uses the `useAccounting` hook
3. **Given** an API endpoint URL changes, **When** the service layer is updated, **Then** all consuming pages are updated automatically

---

### User Story 3 - Journal Entry Validation & Submission (Priority: P1)

As an accountant, I want to create journal entries with real-time balance validation so that I never submit an unbalanced entry.

**Why this priority**: Core accounting integrity requirement — journal entries must always balance. This is a non-negotiable business rule.

**Independent Test**: Create a journal entry with Dr 100, Cr 50. Verify the submit button is disabled and an imbalance warning is shown. Add another Cr 50 and verify submission becomes enabled.

**Acceptance Scenarios**:

1. **Given** I am on the journal entry form, **When** I enter debit and credit amounts, **Then** the running totals for debit and credit are displayed in real time
2. **Given** the total debit does not equal total credit, **When** I try to submit, **Then** the submit button is disabled and an error message is shown
3. **Given** the totals balance and all required fields are filled, **When** I submit, **Then** the entry is saved and I am redirected to the entries list

---

### User Story 4 - Read-Only Ledger & Report Views (Priority: P2)

As a manager, I want to view the general ledger for any account and generate financial reports so that I can monitor financial activity.

**Why this priority**: Reporting is important but depends on journal entries existing in the system first.

**Independent Test**: Navigate to a ledger page for a specific account and verify running balances are calculated correctly. Generate a Trial Balance report and verify debits equal credits.

**Acceptance Scenarios**:

1. **Given** I am on the ledger page, **When** I select an account, **Then** I see all journal lines for that account sorted by date with running balance
2. **Given** I am on the reports page, **When** I select Trial Balance and a date range, **Then** I see all accounts with debit/credit totals that balance

---

### Edge Cases

- What happens when an account has no transactions? The ledger should show an empty state, not an error.
- What happens when a user navigates away from an unsaved journal entry form? The user should be prompted to confirm navigation.
- What happens when the API returns an error? A descriptive error message should be displayed, not a generic failure.
- What happens when a posted entry is modified? The system must prevent any modification to posted entries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST organize accounting components into domain-specific subdirectories: `accounts/`, `journal/`, `ledger/`, `reports/`
- **FR-002**: System MUST provide a centralized API service (`accountingService.js`) that exposes methods for all accounting endpoints
- **FR-003**: System MUST provide a shared state hook (`useAccounting.js`) that manages accounts list, loading state, and error state
- **FR-004**: System MUST provide shared UI components (`Table.jsx`, `Modal.jsx`, `Button.jsx`, `Input.jsx`) used consistently across all accounting pages
- **FR-005**: Journal entry form MUST display real-time debit and credit totals
- **FR-006**: Journal entry form MUST disable submission when totals are imbalanced
- **FR-007**: Journal entry form MUST require at least two lines before submission
- **FR-008**: Account selection in journal lines MUST be required — an entry cannot be submitted with an unassigned account
- **FR-009**: Posted journal entries MUST NOT be editable or deletable
- **FR-010**: Ledger view MUST display transactions sorted by date with a running balance column
- **FR-011**: Report views MUST support three report types: Trial Balance, Income Statement, and Balance Sheet
- **FR-012**: All pages MUST show loading indicators during API calls
- **FR-013**: All pages MUST display user-friendly error messages on API failures
- **FR-014**: System MUST prompt users before discarding unsaved changes on the journal entry form
- **FR-015**: Account select dropdown MUST be searchable and optionally show hierarchy

### Key Entities *(include if feature involves data)*

- **Account**: Financial account (Asset, Liability, Equity, Revenue, Expense) with hierarchical parent-child relationships
- **Journal Entry**: A dated financial transaction with reference, description, and multiple lines that must balance (debits = credits)
- **Journal Entry Line**: Individual debit or credit entry within a journal entry, linked to a specific account
- **Ledger Entry**: Aggregated view of all journal lines for a given account with running balance
- **Report Data**: Generated financial reports (Trial Balance, Income Statement, Balance Sheet) derived from journal entries

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All accounting pages render within 2 seconds on a standard corporate workstation
- **SC-002**: Users can complete journal entry creation in under 3 minutes for a typical entry (2-5 lines)
- **SC-003**: Journal entry form detects and reports imbalance within 200ms of the last input
- **SC-004**: Zero imbalanced journal entries are submitted through the UI validation
- **SC-005**: The ledger running balance calculation is accurate to 4 decimal places for any account with transactions
- **SC-006**: All three financial reports render with correctly balanced totals on first load

## Assumptions

- Users have modern web browsers (Chrome, Firefox, Edge) with JavaScript enabled
- The existing JWT authentication system and tenant isolation middleware are already in place and reused
- The backend APIs for accounts, journal entries, ledger, and reports are already implemented and available at the existing endpoints
- Mobile responsiveness is out of scope for this phase
- User roles and permissions are enforced by the backend — the frontend only needs to route users to appropriate pages
- The existing accounting frontend implementation (feature 006) serves as the base to be refactored
- API base URL and axios instance are configured globally in the existing `api.js` service
