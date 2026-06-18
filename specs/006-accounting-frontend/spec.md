# Feature Specification: Accounting Frontend

**Feature Branch**: `006-accounting-frontend`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Accounting Frontend - Chart of Accounts, Journal Entries, Ledger, Reports"

## User Scenarios & Testing

### User Story 1 - Chart of Accounts Management (Priority: P1)

An accountant needs to view and manage the company's chart of accounts — a hierarchical list of all financial accounts (Asset, Liability, Equity, Revenue, Expense). They must be able to see the account tree with parent-child relationships, expand/collapse nodes, and create new accounts or edit existing ones.

**Why this priority**: The chart of accounts is the foundational structure required before any journal entries can be recorded.

**Independent Test**: Can be fully tested by an accountant logging in, navigating to the Chart of Accounts page, viewing the tree, creating a new account, and editing an existing account.

**Acceptance Scenarios**:

1. **Given** the accountant is logged into the system, **When** they navigate to `/accounting/accounts`, **Then** they see a hierarchical tree of accounts grouped by type (Asset, Liability, Equity, Revenue, Expense).
2. **Given** the chart of accounts page is displayed, **When** the accountant clicks "Create Account", **Then** a form appears with fields for name, type, and optional parent account, and submitting creates the account.
3. **Given** an existing account is displayed, **When** the accountant clicks "Edit", **Then** they can modify the account name or type, and changes are saved.
4. **Given** an account with no transactions or child accounts is selected, **When** the accountant chooses to deactivate it, **Then** the account is soft-deleted and no longer appears in active lists.

---

### User Story 2 - Journal Entry Creation & Posting (Priority: P1)

An accountant needs to record financial transactions by creating journal entries with at least two lines (debits and credits). The system must enforce that total debits equal total credits before the entry can be saved or posted.

**Why this priority**: Journal entries are the core mechanism for recording all financial activity; without this, the system cannot function as an accounting tool.

**Independent Test**: Can be fully tested by creating a journal entry with two lines (one debit, one credit) of equal value, verifying the balance check passes, and posting the entry.

**Acceptance Scenarios**:

1. **Given** the accountant is on the new journal entry form, **When** they add two or more lines with debits and credits, **Then** the running total shows the current balance and whether debits equal credits.
2. **Given** a journal entry where debits do not equal credits, **When** the accountant attempts to save, **Then** the system rejects the entry with a clear error message indicating the imbalance.
3. **Given** a balanced journal entry is ready to post, **When** the accountant clicks "Post", **Then** the entry is locked and can no longer be edited.
4. **Given** an entry has fewer than two lines, **When** the accountant attempts to save, **Then** the system rejects the entry with an error requiring at least two lines.

---

### User Story 3 - Ledger View (Priority: P2)

An accountant needs to view the ledger for a specific account — a chronological list of all transactions affecting that account, with running balances, to audit or verify account activity.

**Why this priority**: The ledger is a core accounting report needed for reconciliation and audit, but can function once journal entries exist.

**Independent Test**: Can be tested by selecting an account with posted journal entries and verifying the ledger displays all transactions in date order with correct running balances.

**Acceptance Scenarios**:

1. **Given** posted journal entries exist for an account, **When** the accountant navigates to the ledger for that account, **Then** they see all transactions sorted by date with debit, credit, and running balance columns.
2. **Given** the ledger view is displayed, **When** the accountant filters by a date range, **Then** only transactions within that range are shown, and the running balance reflects only those transactions.

---

### User Story 4 - Financial Reports (Priority: P2)

A manager or accountant needs to generate financial reports (Trial Balance, Income Statement, Balance Sheet) to assess the company's financial health.

**Why this priority**: Reports provide the business value from accounting data, but depend on journal entries and accounts being in place.

**Independent Test**: Can be tested by selecting a report type and date range, and verifying the report displays correctly calculated figures based on posted journal entries.

**Acceptance Scenarios**:

1. **Given** posted journal entries exist across multiple accounts, **When** the manager selects "Trial Balance" and a date range, **Then** the report shows all accounts with their debit and credit balances at the period end.
2. **Given** posted journal entries exist, **When** the manager selects "Income Statement", **Then** the report shows revenue and expense accounts with net income/loss.
3. **Given** posted journal entries exist, **When** the manager selects "Balance Sheet", **Then** the report shows assets, liabilities, and equity with the accounting equation balanced.

---

### Edge Cases

- What happens when a user navigates to an account's ledger URL directly (e.g., `/accounting/ledger/nonexistent-id`)? The system should show a "not found" error.
- How does the journal entry form behave when a user clears all lines? The form should prevent submission and show a validation error.
- What if the API returns an error during account creation? The form should display the server error inline without losing entered data.
- How does the reports page behave when no entries exist for the selected period? It should show zero balances or an "no data" message.
- What happens when a user tries to edit a posted (locked) entry? The edit option should not be available.
- How does the account tree handle very long account names? Names should truncate with ellipsis and show full name on hover.

## Requirements

### Functional Requirements

- **FR-001**: Accountants MUST be able to view the chart of accounts as a hierarchical tree with expand/collapse for parent-child relationships.
- **FR-002**: Accountants MUST be able to create new accounts by providing a name, selecting a type (Asset, Liability, Equity, Revenue, Expense), and optionally choosing a parent account.
- **FR-003**: Accountants MUST be able to edit existing account names and types.
- **FR-004**: Accountants MUST be able to deactivate (soft-delete) accounts that have no transactions or child accounts.
- **FR-005**: Accountants MUST be able to create journal entries with at least two lines, each specifying an account, a debit amount, or a credit amount.
- **FR-006**: The system MUST validate that total debits equal total credits before allowing a journal entry to be saved or posted.
- **FR-007**: The system MUST display the running balance (total debits vs total credits) in real time as the user adds or modifies journal lines.
- **FR-008**: Once a journal entry is posted, the system MUST lock it so no further edits are permitted.
- **FR-009**: Accountants MUST be able to view a ledger for any account, showing all posted transactions in date order with date, description, debit, credit, and running balance columns.
- **FR-010**: The ledger view MUST support filtering by date range.
- **FR-011**: Managers MUST be able to view a Trial Balance report showing all accounts with their end-of-period debit and credit balances.
- **FR-012**: Managers MUST be able to view an Income Statement report showing revenue, expenses, and net income/loss for a given period.
- **FR-013**: Managers MUST be able to view a Balance Sheet report showing assets, liabilities, and equity as of a given date.
- **FR-014**: All pages MUST display meaningful error messages from the API inline and show validation errors per field.
- **FR-015**: Submit buttons on all forms MUST be disabled during API calls to prevent double submission.
- **FR-016**: The chart of accounts page MUST display skeleton loaders while data is loading.
- **FR-017**: Only users with Accountant or Manager roles (per the permission matrix) MUST be able to access accounting features.

### Key Entities

- **Account**: A named category in the chart of accounts with a type (Asset, Liability, Equity, Revenue, Expense), an optional parent account for hierarchy, and an active/inactive status.
- **Journal Entry**: A dated, described record of a financial transaction with a unique reference, composed of two or more journal entry lines that must balance (total debits = total credits).
- **Journal Entry Line**: A single line within a journal entry linking an account to either a debit or credit amount.
- **Ledger**: A chronological view of all journal entry lines for a specific account, showing running balance.
- **Report**: A summarized financial view (Trial Balance, Income Statement, Balance Sheet) computed from posted journal entries filtered by date range.

## Success Criteria

### Measurable Outcomes

- **SC-001**: An accountant can create a new account in under 30 seconds from the chart of accounts page.
- **SC-002**: An accountant can create and post a two-line journal entry in under 1 minute.
- **SC-003**: A manager can generate a Trial Balance report for any date range in under 5 seconds (excluding data loading time).
- **SC-004**: An accountant can view the ledger for any account and verify the running balance matches manual calculation.
- **SC-005**: 100% of journal entries created through the UI satisfy the balancing constraint (debits = credits) on first save attempt.
- **SC-006**: The chart of accounts page loads and displays the account tree within 3 seconds under normal network conditions.

## Assumptions

- Existing authentication (JWT) and multi-tenancy systems handle user identity and tenant scoping.
- The accounting backend APIs are already implemented and available at the expected endpoints.
- The frontend uses the established React framework with the existing API client pattern.
- The permission/role system already distinguishes Accountant and Manager roles appropriately.
- Financial data uses a single currency for MVP (no multi-currency support in this iteration).
- Mobile responsiveness is not required for MVP — the interface targets desktop screens.
- The user has an active internet connection and a modern web browser.
- This feature does not include CSV import, PDF export, or AI-powered suggestions (listed as future enhancements).
