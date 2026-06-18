# Feature Specification: Accounting Schema

**Feature Branch**: `005-accounting-schema`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Phase D3 — Accounting Schema (MOST CRITICAL). Accounts with hierarchical structure (parent_id) and types: Asset, Liability, Equity, Revenue, Expense. Journal Entries with header table and lines table. HARD RULE: No journal entry without balanced lines."

## User Scenarios & Accounting *(mandatory)*

### User Story 1 - Accountant manages the Chart of Accounts (Priority: P1)

An accountant or administrator needs to create, organize, and maintain the chart of accounts — a structured list of all accounts used by the organization. Accounts are organized hierarchically (parent-child) to support roll-up reporting.

**Why this priority**: The chart of accounts is the foundational data structure for all accounting. No transactions can be recorded until accounts exist to post against.

**Independent Test**: An authenticated user with appropriate permissions can create a new account with a specified type and parent, and the account appears correctly in the hierarchy.

**Acceptance Scenarios**:

1. **Given** an authenticated user with accounting privileges, **When** they create a new account with a name, type (e.g., Asset), and an optional parent account, **Then** the account is created and can be referenced by journal entries.
2. **Given** an existing account hierarchy (e.g., Assets > Current Assets > Cash), **When** a user views the chart of accounts, **Then** they see the full tree structure with parent-child relationships preserved.
3. **Given** an account that has child accounts, **When** someone attempts to delete it, **Then** the system prevents deletion until all child accounts are reassigned or removed.
4. **Given** a list of accounts, **When** a user filters by account type (e.g., show only Revenue accounts), **Then** only accounts of that type are returned.

---

### User Story 2 - Accountant records journal entries (Priority: P1)

An accountant needs to record financial transactions as journal entries, each consisting of a header (date, description, reference) and multiple lines (account, debit amount, credit amount). The system enforces that every entry is balanced.

**Why this priority**: Recording transactions is the core purpose of the accounting system. The balanced-entry rule is a constitutional requirement — no unbalanced entry can ever be persisted.

**Independent Test**: A user can create a journal entry with two or more lines where total debits equal total credits. An attempt to save an unbalanced entry (total debits ≠ total credits) is rejected by the system.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they create a journal entry with a date, description, reference number, and a set of lines where total debits equal total credits, **Then** the entry is saved successfully.
2. **Given** an authenticated user, **When** they attempt to create a journal entry where total debits do not equal total credits, **Then** the system rejects the entry with a clear error message.
3. **Given** an existing journal entry, **When** a user views its details, **Then** they see the header information and all associated lines with their respective debits and credits.
4. **Given** a journal entry with lines, **When** a user lists entries for a date range, **Then** only entries within that range are returned, ordered by date.

---

### User Story 3 - System enforces accounting data integrity (Priority: P1)

The accounting system must guarantee that all persisted journal entries are balanced. This is enforced at the data layer, not just the user interface.

**Why this priority**: Constitution mandates that no journal entry exist without balanced lines. This is a hard constraint that must hold at the database level regardless of the entry method (API, bulk import, future features).

**Independent Test**: Any attempt to directly insert an unbalanced journal entry at the data layer is rejected, and no existing entry can become unbalanced through data modification.

**Acceptance Scenarios**:

1. **Given** any journal entry in the system, **When** its lines are queried, **Then** the sum of all debit amounts always equals the sum of all credit amounts.
2. **Given** a database-level constraint on the lines table, **When** an insert, update, or delete operation would leave an entry unbalanced, **Then** the operation is rejected by the database.

---

### Edge Cases

- What happens when a user tries to delete the only line of a two-line journal entry? → The system must prevent the deletion if it would unbalance the entry, or require both lines to be removed (deleting the entire entry).
- What happens when an account is referenced by existing journal entry lines? → The account should not be deletable until all referencing journal entry lines are removed or reassigned.
- What is the maximum depth of the account hierarchy? → A reasonable limit (e.g., 10 levels) should be enforced to prevent infinite nesting and performance issues.
- Can an account change its type after being used in journal entries? → Once an account has been posted to, its type should be frozen to maintain historical accuracy.
- What about zero-amount journal entries? → An entry where all lines have zero debits and zero credits is trivially balanced but has no economic substance. The system should reject entries where every line amount is zero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a chart of accounts where each account has a name, a unique identifier, and exactly one of the five types: Asset, Liability, Equity, Revenue, Expense.
- **FR-002**: Accounts MUST support a hierarchical (parent-child) structure via a self-referencing parent relationship, enabling n-level nesting.
- **FR-003**: An account with child accounts MUST NOT be deletable until all children are removed or reassigned.
- **FR-004**: An account that is referenced by any journal entry line MUST NOT be deletable or have its type changed.
- **FR-005**: The system MUST support creating journal entries consisting of a header (date, description, reference number) and one or more lines (account reference, debit amount, credit amount).
- **FR-006**: The system MUST enforce at both the application layer and the data layer that the sum of all debit amounts equals the sum of all credit amounts for every journal entry (the balanced-entry rule).
- **FR-007**: Journal entries MUST be immutable once created — existing entries cannot be modified or deleted (audit trail requirement).
- **FR-008**: Each journal entry MUST be scoped to a tenant, and the account chart MUST be scoped to a tenant (consistent with the existing multi-tenancy model).
- **FR-009**: All monetary amounts in journal entry lines MUST be non-negative. Debits and credits are direction indicators, not positive/negative values.
- **FR-010**: A journal entry MUST have at least two lines (one debit, one credit) to be valid.
- **FR-011**: The system MUST reject any journal entry where all line amounts are zero.

### Key Entities

- **Account**: A named bucket in the chart of accounts with a type (Asset, Liability, Equity, Revenue, Expense) and an optional parent reference. Forms a tree structure per tenant.
- **Journal Entry Header**: The top-level record of a financial transaction, containing the entry date, description, reference number, and tenant scope. Immutable after creation.
- **Journal Entry Line**: A single line within a journal entry, referencing an account and containing either a debit amount or a credit amount (but not both). Each line is tenant-scoped through its parent entry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An authenticated user can create a valid journal entry (header + 2 lines) with balanced debits and credits in under 3 seconds round-trip including database persistence.
- **SC-002**: All attempts to persist an unbalanced journal entry are rejected with a clear error message, with zero false positives or false negatives.
- **SC-003**: The chart of accounts renders as a complete tree preserving parent-child relationships for any hierarchy up to 10 levels deep, with response time under 2 seconds for up to 500 accounts per tenant.
- **SC-004**: An account once used in a journal entry cannot have its type changed or be deleted, providing a complete and immutable audit trail.
- **SC-005**: The data-layer constraint (balanced-entry rule) is verified to reject direct SQL inserts or updates that would create an unbalanced entry, independent of application-level validation.

## Assumptions

- Account code/numbering scheme (e.g., 1000-series for Assets) will be defined during implementation as a UI concern; the data model stores only the hierarchy and type.
- Multi-currency support is out of scope for this phase. All amounts are in the tenant's base currency.
- Opening/initial balances will be handled in a separate future phase. This phase covers ongoing transaction recording only.
- Fiscal year and accounting period structures are out of scope for this phase. Entries are dated but not assigned to periods.
- The existing multi-tenancy model (tenant-scoped data) applies — all accounts and journal entries belong to exactly one tenant.
- Financial reports (Balance Sheet, Income Statement, Trial Balance) will be addressed in a subsequent phase. This phase builds the data foundation those reports will query.
- The audit trail requirement (immutable entries) means entries are append-only. Corrections are made via adjusting entries, never by modifying or deleting existing entries.
